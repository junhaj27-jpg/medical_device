import hashlib
import socket
import struct
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.audit.services import record_audit

from .file_security import validate_file_content
from .models import Attachment
from .storage_adapters import LocalPrivateStorageAdapter


class MalwareScanner:
    name="unconfigured"
    def scan(self,file_obj): raise RuntimeError("악성코드 검사 엔진이 구성되지 않았습니다.")


class ClamAVScanner(MalwareScanner):
    name="clamav-instream"
    def scan(self,file_obj):
        if not settings.CLAMAV_HOST: raise RuntimeError("CLAMAV_HOST가 설정되지 않았습니다.")
        with socket.create_connection((settings.CLAMAV_HOST,settings.CLAMAV_PORT),timeout=10) as client:
            client.sendall(b"zINSTREAM\0")
            for chunk in iter(lambda:file_obj.read(64*1024),b""):
                client.sendall(struct.pack("!I",len(chunk))+chunk)
            client.sendall(struct.pack("!I",0)); response=client.recv(4096)
        if b"ERROR" in response: raise RuntimeError(response.decode(errors="replace"))
        return b"FOUND" in response

def _can_access(user,event): return user.role in {"RA_QA","ADMIN"} or event.reporter_id==user.pk

@transaction.atomic
def upload_attachment(*,event,user,file_obj,description="",request=None):
    if not _can_access(user,event): raise PermissionDenied("첨부파일 업로드 권한이 없습니다.")
    if Attachment.objects.filter(uploaded_by=user,is_deleted=False).count()>=settings.ATTACHMENT_MAX_FILES_PER_USER: raise ValidationError("사용자별 첨부파일 개수 제한을 초과했습니다.")
    detected=validate_file_content(file_obj); original=Path(file_obj.name).name; extension=Path(original).suffix.lower(); storage_name=f"{uuid.uuid4()}{extension}"
    file_obj.seek(0); digest=hashlib.sha256()
    for chunk in file_obj.chunks(): digest.update(chunk)
    file_obj.seek(0); file_obj.name=storage_name
    attachment=Attachment(adverse_event=event,uploaded_by=user,original_name=original,storage_name=storage_name,file=file_obj,file_type=extension.lstrip("."),detected_mime=detected,sha256=digest.hexdigest(),size=file_obj.size,description=description,scan_status=Attachment.ScanStatus.QUARANTINED)
    attachment.full_clean(); attachment.save(); record_audit(user=user,action="ATTACHMENT_QUARANTINED",target=attachment,after={"sha256":attachment.sha256,"size":attachment.size,"mime":detected},reason="파일 업로드",request=request); return attachment

@transaction.atomic
def process_scan_job(attachment_id,*,scanner=None,actor=None,request=None,now=None):
    attachment=Attachment.objects.select_for_update().get(pk=attachment_id); now=now or timezone.now()
    if attachment.scan_status in {Attachment.ScanStatus.CLEAN,Attachment.ScanStatus.INFECTED}: return attachment
    if attachment.scan_status==Attachment.ScanStatus.SCAN_FAILED or (attachment.scan_next_retry_at and attachment.scan_next_retry_at>now): return attachment
    scanner=scanner or ClamAVScanner()
    try:
        attachment.file.open("rb"); result=scanner.scan(attachment.file); status=Attachment.ScanStatus.INFECTED if result else Attachment.ScanStatus.CLEAN
        attachment.scan_error_code=""; attachment.scan_next_retry_at=None; attachment.scanned_at=now
    except (OSError,RuntimeError,ValueError,TimeoutError):
        attachment.scan_attempts+=1; attachment.scan_error_code="SCANNER_UNAVAILABLE"
        if attachment.scan_attempts>=settings.CLAMAV_SCAN_MAX_ATTEMPTS:
            status=Attachment.ScanStatus.SCAN_FAILED; attachment.scanned_at=now; attachment.scan_next_retry_at=None
        else:
            status=Attachment.ScanStatus.QUARANTINED; delay=settings.CLAMAV_SCAN_BACKOFF_SECONDS*(2**(attachment.scan_attempts-1)); attachment.scan_next_retry_at=now+timezone.timedelta(seconds=delay)
    finally:
        attachment.file.close()
    attachment.scan_status=status; attachment.scan_engine=scanner.name; attachment.save(update_fields=["scan_status","scan_engine","scan_attempts","scan_next_retry_at","scan_error_code","scanned_at"]); record_audit(user=actor,action="ATTACHMENT_SCAN",target=attachment,after={"status":status,"engine":scanner.name,"attempts":attachment.scan_attempts,"next_retry_at":attachment.scan_next_retry_at},reason="악성코드 검사",request=request); return attachment

def scan_attachment(attachment,*,scanner=None,actor=None,request=None):
    process_scan_job(attachment.pk,scanner=scanner,actor=actor,request=request); attachment.refresh_from_db(); return attachment

def run_pending_scan_jobs(*,scanner=None,actor=None,limit=100,now=None):
    now=now or timezone.now(); ids=list(Attachment.objects.filter(scan_status=Attachment.ScanStatus.QUARANTINED).filter(models.Q(scan_next_retry_at__isnull=True)|models.Q(scan_next_retry_at__lte=now)).values_list("id",flat=True)[:limit])
    return [process_scan_job(pk,scanner=scanner,actor=actor,now=now) for pk in ids]

def authorize_download(attachment,user):
    if not _can_access(user,attachment.adverse_event): raise PermissionDenied("첨부파일 다운로드 권한이 없습니다.")
    if attachment.is_deleted or attachment.scan_status!=Attachment.ScanStatus.CLEAN: raise PermissionDenied("검사가 완료된 정상 파일만 다운로드할 수 있습니다.")

def issue_signed_download_url(attachment,*,user,adapter=None,expires_in=None,request=None):
    authorize_download(attachment,user); expires=min(expires_in or settings.SIGNED_URL_EXPIRY_SECONDS,900)
    if expires<=0: raise ValidationError("서명 URL 만료시간이 올바르지 않습니다.")
    adapter=adapter or LocalPrivateStorageAdapter(attachment); url=adapter.signed_url(attachment.file.name,expires_in=expires,subject_id=user.pk)
    record_audit(user=user,action="ATTACHMENT_SIGNED_URL",target=attachment,after={"expires_in":expires,"storage_name":attachment.storage_name},reason="권한 확인 후 단기 다운로드 URL 발급",request=request); return url

@transaction.atomic
def schedule_attachment_deletion(attachment,*,user,reason,request=None):
    if user.role!="ADMIN": raise PermissionDenied("ADMIN만 삭제를 요청할 수 있습니다.")
    if attachment.legal_hold: raise ValidationError("Legal hold가 설정된 파일은 삭제할 수 없습니다.")
    if not reason.strip(): raise ValidationError("삭제 사유가 필요합니다.")
    attachment.is_deleted=True; attachment.deletion_scheduled_at=timezone.now(); attachment.save(update_fields=["is_deleted","deletion_scheduled_at"]); record_audit(user=user,action="ATTACHMENT_DELETE_REQUEST",target=attachment,after={"scheduled_at":attachment.deletion_scheduled_at},reason=reason,request=request,require_reason=True)

@transaction.atomic
def destroy_attachment(attachment,*,user,reason,request=None,destruction_request=None):
    if destruction_request is None: raise ValidationError("승인된 파기 요청이 필요합니다.")
    from apps.compliance.retention_services import execute_attachment_destruction
    return execute_attachment_destruction(destruction_request,attachment,user=user,request=request)
