import io
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection
from django.utils import timezone

from apps.accounts.models import User
from apps.adverse_events.attachment_services import (
    ClamAVScanner,
    authorize_download,
    issue_signed_download_url,
    process_scan_job,
    scan_attachment,
    upload_attachment,
)
from apps.adverse_events.file_security import validate_file_content
from apps.adverse_events.models import AdverseEvent, Attachment
from apps.approvals.models import ElectronicSignature
from apps.approvals.services import approve_capa, approve_investigation, request_signature_review, verify_signature
from apps.audit.models import AuditExportOutbox, AuditLog
from apps.audit.outbox_services import process_one_outbox
from apps.audit.services import record_audit, verify_audit_chain, verify_audit_chain_detailed
from apps.capa.models import CAPA
from apps.capa.services import update_capa
from apps.compliance.models import AnnualSequence
from apps.compliance.retention_services import (
    decide_destruction,
    decide_legal_hold,
    execute_attachment_destruction,
    request_destruction,
    request_legal_hold,
)
from apps.compliance.services import next_management_number
from apps.devices.models import DeviceLot, MedicalDevice
from apps.investigations.models import Investigation
from apps.reports.services import approve_report, create_report_from_event, request_report_review, update_report

pytestmark=pytest.mark.django_db

@pytest.fixture
def security_data():
    admin=User.objects.create_user("sec-admin",password="Pass1234!",role="ADMIN")
    ra=User.objects.create_user("sec-ra",password="Pass1234!",role="RA_QA")
    staff=User.objects.create_user("sec-staff",password="Pass1234!",role="STAFF")
    device=MedicalDevice.objects.create(device_code="SEC",product_name="Secure",model_name="M",manufacturer="Maker",product_category="Monitor",approval_number="SEC-A",risk_class="II")
    lot=DeviceLot.objects.create(medical_device=device,lot_number="SEC-L",manufacture_date=timezone.localdate())
    event=AdverseEvent.objects.create(title="Security",description="Desc",medical_device=device,device_lot=lot,reporter=staff,occurred_at=timezone.now(),event_location="Hospital",severity="HIGH",event_type="Failure")
    return admin,ra,staff,event

def test_sequence_resets_by_year():
    assert next_management_number("CAPA",year=2030)=="CAPA-2030-000001"
    assert next_management_number("CAPA",year=2030)=="CAPA-2030-000002"
    assert next_management_number("CAPA",year=2031)=="CAPA-2031-000001"

@pytest.mark.skipif(connection.vendor!="postgresql",reason="PostgreSQL row-lock integration test")
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_concurrent_sequence_generation_postgresql():
    def generate(_):
        close_old_connections()
        try: return next_management_number("REGULATORY_REPORT",year=2040)
        finally: close_old_connections()
    with ThreadPoolExecutor(max_workers=8) as pool: numbers=list(pool.map(generate,range(20)))
    assert len(numbers)==len(set(numbers))==20
    assert AnnualSequence.objects.get(document_type="REGULATORY_REPORT",year=2040).value==20

def test_audit_chain_detects_tampering_and_redacts(security_data):
    admin,ra,staff,event=security_data
    log=record_audit(user=admin,action="SECURITY_TEST",target=event,after={"status":"REVIEWED","password":"never-log","api_key":"secret"},reason="테스트")
    assert log.after_data["password"]=="[REDACTED]" and log.after_data["api_key"]=="[REDACTED]"
    assert verify_audit_chain()==[]
    AuditLog.objects.filter(pk=log.pk).update(after_data={"status":"TAMPERED"})
    assert verify_audit_chain()==[log.pk]

def test_audit_hmac_key_rotation_and_missing_historical_key(security_data,settings):
    admin,ra,staff,event=security_data
    settings.AUDIT_HMAC_KEY=""; settings.AUDIT_HMAC_KEYS='{"old":"old-test-key","new":"new-test-key"}'; settings.AUDIT_ACTIVE_KEY_ID="old"
    old_log=record_audit(user=admin,action="OLD_KEY",target=event,reason="rotation test")
    settings.AUDIT_ACTIVE_KEY_ID="new"
    new_log=record_audit(user=admin,action="NEW_KEY",target=event,reason="rotation test")
    assert old_log.key_id=="old" and new_log.key_id=="new"
    assert {r["status"] for r in verify_audit_chain_detailed()}=={"VALID"}
    settings.AUDIT_HMAC_KEYS='{"new":"new-test-key"}'
    results={r["id"]:r["status"] for r in verify_audit_chain_detailed()}
    assert results[old_log.pk]=="KEY_UNAVAILABLE" and results[new_log.pk]=="VALID"

def test_audit_outbox_retries_idempotently_without_changing_log(security_data,settings):
    admin,ra,staff,event=security_data; settings.AUDIT_EXPORT_MAX_ATTEMPTS=3; settings.AUDIT_EXPORT_BACKOFF_SECONDS=1
    log=record_audit(user=admin,action="OUTBOX_TEST",target=event,reason="outbox")
    original_hash=log.current_hash; keys=[]
    class FlakyExporter:
        def export(self,*,idempotency_key,payload):
            keys.append(idempotency_key)
            if len(keys)<2: raise TimeoutError("temporary")
            return {"accepted":True}
    first=process_one_outbox(FlakyExporter()); assert first.status=="RETRY" and first.attempts==1
    AuditExportOutbox.objects.filter(pk=first.pk).update(next_retry_at=None)
    second=process_one_outbox(FlakyExporter()); assert second.status=="SENT" and second.attempts==2 and keys[0]==keys[1]
    log.refresh_from_db(); assert log.current_hash==original_hash

def test_audit_outbox_max_failure_preserves_original(security_data,settings):
    admin,ra,staff,event=security_data; settings.AUDIT_EXPORT_MAX_ATTEMPTS=1
    log=record_audit(user=admin,action="OUTBOX_FAIL",target=event,reason="outbox")
    class FailedExporter:
        def export(self,**kwargs): raise RuntimeError("offline")
    outbox=process_one_outbox(FailedExporter()); assert outbox.status=="FAILED" and AuditLog.objects.filter(pk=log.pk).exists()

def test_signature_reauthentication_reason_self_approval_and_invalidation(security_data):
    admin,ra,staff,event=security_data
    report=create_report_from_event(event,ra,regulatory_authority="MFDS"); request_report_review(report,ra)
    with pytest.raises(ValidationError): approve_report(report,admin,password="wrong",reason="검토")
    with pytest.raises(ValidationError): approve_report(report,admin,password="Pass1234!",reason="")
    report.created_by=admin; report.save(update_fields=["created_by"])
    with pytest.raises(PermissionDenied): approve_report(report,admin,password="Pass1234!",reason="검토")
    report.created_by=ra; report.save(update_fields=["created_by"])
    approve_report(report,admin,password="Pass1234!",reason="내용 확인")
    signature=ElectronicSignature.objects.get(target_model="RegulatoryReport",target_id=str(report.pk))
    assert verify_signature(signature)
    canonical=signature.canonical_data; ElectronicSignature.objects.filter(pk=signature.pk).update(canonical_data={"tampered":True}); signature.refresh_from_db(); assert not verify_signature(signature)
    ElectronicSignature.objects.filter(pk=signature.pk).update(canonical_data=canonical); signature.refresh_from_db(); assert verify_signature(signature)
    update_report(report,ra,title="변경된 보고서")
    signature.refresh_from_db(); report.refresh_from_db()
    assert not verify_signature(signature) and report.report_status=="DRAFT"

def test_file_content_quarantine_scan_and_download_controls(security_data,tmp_path):
    admin,ra,staff,event=security_data
    field=Attachment._meta.get_field("file"); field.storage._location=str(tmp_path)
    disguised=SimpleUploadedFile("bad.pdf",b"MZ executable",content_type="application/pdf")
    with pytest.raises(ValidationError): validate_file_content(disguised)
    with pytest.raises(ValidationError): validate_file_content(SimpleUploadedFile("double.exe.pdf",b"%PDF-1.7",content_type="application/pdf"))
    clean_file=SimpleUploadedFile("evidence.pdf",b"%PDF-1.7\nclean",content_type="application/pdf")
    attachment=upload_attachment(event=event,user=staff,file_obj=clean_file)
    assert attachment.scan_status=="QUARANTINED" and attachment.sha256 and attachment.original_name=="evidence.pdf"
    with pytest.raises(PermissionDenied): authorize_download(attachment,staff)
    class CleanScanner:
        name="mock-clamav"
        def scan(self,file_obj): return False
    scan_attachment(attachment,scanner=CleanScanner(),actor=admin); authorize_download(attachment,staff)
    other=User.objects.create_user("other-file-user",password="Pass1234!",role="STAFF")
    with pytest.raises(PermissionDenied): authorize_download(attachment,other)

def test_eicar_and_scan_failure_are_not_downloadable(security_data,tmp_path):
    admin,ra,staff,event=security_data; Attachment._meta.get_field("file").storage._location=str(tmp_path)
    attachment=upload_attachment(event=event,user=staff,file_obj=SimpleUploadedFile("eicar.pdf",b"%PDF-1.7\nEICAR",content_type="application/pdf"))
    class EicarScanner:
        name="mock-clamav"
        def scan(self,file_obj): return b"EICAR" in file_obj.read()
    scan_attachment(attachment,scanner=EicarScanner(),actor=admin)
    assert attachment.scan_status=="INFECTED"
    with pytest.raises(PermissionDenied): authorize_download(attachment,staff)
    failed=upload_attachment(event=event,user=staff,file_obj=SimpleUploadedFile("failed.pdf",b"%PDF-1.7\nscan",content_type="application/pdf"))
    for attempt in range(3):
        failed.scan_next_retry_at=None; failed.save(update_fields=["scan_next_retry_at"]); scan_attachment(failed,actor=admin); failed.refresh_from_db()
    assert failed.scan_status=="SCAN_FAILED"
    with pytest.raises(PermissionDenied): authorize_download(failed,staff)

def test_request_id_middleware_returns_correlation_header(client):
    response=client.get("/")
    assert response.headers["X-Request-ID"]

def test_scan_job_is_idempotent_and_uses_backoff(security_data,tmp_path,settings):
    admin,ra,staff,event=security_data; Attachment._meta.get_field("file").storage._location=str(tmp_path); settings.CLAMAV_SCAN_MAX_ATTEMPTS=2; settings.CLAMAV_SCAN_BACKOFF_SECONDS=5
    attachment=upload_attachment(event=event,user=staff,file_obj=SimpleUploadedFile("retry.pdf",b"%PDF-1.7\nretry",content_type="application/pdf"))
    first=process_scan_job(attachment.pk,actor=admin); assert first.scan_status=="QUARANTINED" and first.scan_attempts==1 and first.scan_next_retry_at
    same=process_scan_job(attachment.pk,actor=admin); assert same.scan_attempts==1
    first.scan_next_retry_at=None; first.save(update_fields=["scan_next_retry_at"]); final=process_scan_job(attachment.pk,actor=admin); assert final.scan_status=="SCAN_FAILED" and final.scan_attempts==2

def test_object_storage_signed_url_requires_access_and_caps_expiry(security_data,tmp_path):
    admin,ra,staff,event=security_data; Attachment._meta.get_field("file").storage._location=str(tmp_path)
    attachment=upload_attachment(event=event,user=staff,file_obj=SimpleUploadedFile("object.pdf",b"%PDF-1.7\nobject",content_type="application/pdf")); Attachment.objects.filter(pk=attachment.pk).update(scan_status="CLEAN"); attachment.refresh_from_db()
    class MockAdapter:
        def signed_url(self,key,*,expires_in,subject_id): assert expires_in==900; return f"https://objects.invalid/{key}?subject={subject_id}"
    url=issue_signed_download_url(attachment,user=staff,adapter=MockAdapter(),expires_in=9999); assert url.startswith("https://objects.invalid/")
    other=User.objects.create_user("object-other",password="Pass1234!",role="STAFF")
    with pytest.raises(PermissionDenied): issue_signed_download_url(attachment,user=other,adapter=MockAdapter())

def test_legal_hold_blocks_destruction_and_separates_approver(security_data,tmp_path):
    admin,ra,staff,event=security_data; second_admin=User.objects.create_user("hold-admin",password="Pass1234!",role="ADMIN"); Attachment._meta.get_field("file").storage._location=str(tmp_path)
    attachment=upload_attachment(event=event,user=staff,file_obj=SimpleUploadedFile("hold.pdf",b"%PDF-1.7\nhold",content_type="application/pdf")); hold=request_legal_hold(attachment,user=admin,reason="소송 보존")
    with pytest.raises(PermissionDenied): decide_legal_hold(hold,user=admin,approve=True,reason="승인")
    decide_legal_hold(hold,user=second_admin,approve=True,reason="보존 승인"); destruction=request_destruction(attachment,user=admin,reason="만료 파기")
    with pytest.raises(ValidationError): decide_destruction(destruction,user=second_admin,approve=True,reason="파기 승인")

def test_destruction_requires_different_approver_and_is_idempotent(security_data,tmp_path):
    admin,ra,staff,event=security_data; second_admin=User.objects.create_user("destroy-admin",password="Pass1234!",role="ADMIN"); Attachment._meta.get_field("file").storage._location=str(tmp_path)
    attachment=upload_attachment(event=event,user=staff,file_obj=SimpleUploadedFile("destroy.pdf",b"%PDF-1.7\ndestroy",content_type="application/pdf")); item=request_destruction(attachment,user=admin,reason="정책 만료")
    with pytest.raises(PermissionDenied): decide_destruction(item,user=admin,approve=True,reason="승인")
    decide_destruction(item,user=second_admin,approve=True,reason="독립 승인"); execute_attachment_destruction(item,attachment,user=second_admin); executed_at=item.executed_at; execute_attachment_destruction(item,attachment,user=second_admin); assert item.executed_at==executed_at and attachment.destroyed_at

def test_capa_signature_self_approval_and_reapproval_after_change(security_data):
    admin,ra,staff,event=security_data
    capa=CAPA.objects.create(adverse_event=event,issue_description="Issue",root_cause="Cause",action_plan="Plan",owner=ra,created_by=ra,planned_completion_date=timezone.localdate()+timezone.timedelta(days=5))
    request_signature_review(capa,user=ra); approve_capa(capa,user=admin,password="Pass1234!",reason="승인"); capa.refresh_from_db(); assert capa.approval_status=="APPROVED"
    update_capa(capa,ra,issue_description="Changed"); capa.refresh_from_db(); assert capa.approval_status=="NEEDS_REAPPROVAL" and capa.approval_version==2
    own=CAPA.objects.create(adverse_event=event,issue_description="Own",owner=admin,created_by=admin,planned_completion_date=timezone.localdate()+timezone.timedelta(days=5)); request_signature_review(own,user=admin)
    with pytest.raises(PermissionDenied): approve_capa(own,user=admin,password="Pass1234!",reason="자기 승인")

def test_investigation_signature_self_approval_blocked(security_data):
    admin,ra,staff,event=security_data
    investigation=Investigation.objects.create(adverse_event=event,investigator=admin,investigation_summary="Summary",root_cause="Cause",investigation_method="Method",started_at=timezone.now()); request_signature_review(investigation,user=admin)
    with pytest.raises(PermissionDenied): approve_investigation(investigation,user=admin,password="Pass1234!",reason="자기 승인")

@pytest.mark.clamav_integration
@pytest.mark.skipif(not os.getenv("RUN_CLAMAV_INTEGRATION"),reason="RUN_CLAMAV_INTEGRATION is not enabled")
def test_real_clamav_eicar_integration():
    scanner=ClamAVScanner(); sample=io.BytesIO(b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")
    assert scanner.scan(sample) is True

def test_zip_bomb_ratio_is_rejected(settings):
    settings.ATTACHMENT_MAX_COMPRESSION_RATIO=2
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml","x"); archive.writestr("word/document.xml","A"*10000)
    upload=SimpleUploadedFile("bomb.docx",stream.getvalue(),content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    with pytest.raises(ValidationError): validate_file_content(upload)
