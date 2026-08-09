from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit

from .models import DestructionRequest, LegalHold, RetentionPolicy


def target_ref(target): return target.__class__.__name__,str(target.pk)

def calculate_retention_expiry(target,as_of=None):
    as_of=as_of or timezone.localdate(); record_type=target.__class__.__name__; policy=RetentionPolicy.objects.filter(record_type=record_type,effective_from__lte=as_of).order_by("-effective_from","-version").first()
    if not policy: raise ValidationError(f"{record_type} 보존정책이 설정되지 않았습니다.")
    basis=getattr(target,"created_at",timezone.now()); return basis+timezone.timedelta(days=policy.retention_days)

@transaction.atomic
def create_retention_policy(*,record_type,version,effective_from,retention_days,user,request=None):
    if user.role!="ADMIN": raise PermissionDenied("ADMIN만 보존정책 버전을 만들 수 있습니다.")
    policy=RetentionPolicy.objects.create(record_type=record_type,version=version,effective_from=effective_from,retention_days=retention_days,created_by=user); record_audit(user=user,action="RETENTION_POLICY_CREATE",target=policy,reason="새 보존정책 버전",request=request); return policy

@transaction.atomic
def request_legal_hold(target,*,user,reason,request=None):
    if not reason.strip(): raise ValidationError("legal hold 요청 사유가 필요합니다.")
    model,pk=target_ref(target); hold=LegalHold.objects.create(target_model=model,target_id=pk,requested_by=user,request_reason=reason); record_audit(user=user,action="LEGAL_HOLD_REQUEST",target=hold,reason=reason,request=request,require_reason=True); return hold

@transaction.atomic
def decide_legal_hold(hold,*,user,approve,reason,request=None):
    if user.role!="ADMIN": raise PermissionDenied("ADMIN만 legal hold를 승인 또는 반려할 수 있습니다.")
    if user.pk==hold.requested_by_id: raise PermissionDenied("legal hold 요청자는 자신의 요청을 승인할 수 없습니다.")
    if hold.status!=LegalHold.Status.REQUESTED or not reason.strip(): raise ValidationError("처리 가능한 요청과 결정 사유가 필요합니다.")
    hold.status=LegalHold.Status.APPROVED if approve else LegalHold.Status.REJECTED; hold.approved_by=user; hold.approved_at=timezone.now(); hold.decision_reason=reason; hold.save(); record_audit(user=user,action="LEGAL_HOLD_APPROVE" if approve else "LEGAL_HOLD_REJECT",target=hold,reason=reason,request=request,require_reason=True); return hold

@transaction.atomic
def release_legal_hold(hold,*,user,reason,request=None):
    if user.role!="ADMIN" or hold.status!=LegalHold.Status.APPROVED: raise PermissionDenied("승인된 legal hold는 ADMIN만 해제할 수 있습니다.")
    if not reason.strip(): raise ValidationError("legal hold 해제 사유가 필요합니다.")
    hold.status=LegalHold.Status.RELEASED; hold.released_by=user; hold.released_at=timezone.now(); hold.decision_reason=reason; hold.save(); record_audit(user=user,action="LEGAL_HOLD_RELEASE",target=hold,reason=reason,request=request,require_reason=True); return hold

@transaction.atomic
def request_destruction(target,*,user,reason,request=None):
    if not reason.strip(): raise ValidationError("파기 사유가 필요합니다.")
    model,pk=target_ref(target); item=DestructionRequest.objects.create(target_model=model,target_id=pk,requested_by=user,reason=reason); record_audit(user=user,action="DESTRUCTION_REQUEST",target=item,reason=reason,request=request,require_reason=True); return item

@transaction.atomic
def decide_destruction(item,*,user,approve,reason,request=None):
    if user.role!="ADMIN": raise PermissionDenied("ADMIN만 파기를 승인 또는 반려할 수 있습니다.")
    if user.pk==item.requested_by_id: raise PermissionDenied("파기 요청자는 자신의 요청을 승인할 수 없습니다.")
    if item.status!=DestructionRequest.Status.REQUESTED or not reason.strip(): raise ValidationError("처리 가능한 요청과 결정 사유가 필요합니다.")
    if approve and LegalHold.objects.filter(target_model=item.target_model,target_id=item.target_id,status=LegalHold.Status.APPROVED).exists(): raise ValidationError("legal hold 대상은 파기 승인할 수 없습니다.")
    item.status=DestructionRequest.Status.APPROVED if approve else DestructionRequest.Status.REJECTED; item.approved_by=user; item.approved_at=timezone.now(); item.decision_reason=reason; item.save(); record_audit(user=user,action="DESTRUCTION_APPROVE" if approve else "DESTRUCTION_REJECT",target=item,reason=reason,request=request,require_reason=True); return item

@transaction.atomic
def execute_attachment_destruction(item,attachment,*,user,request=None):
    if item.status==DestructionRequest.Status.EXECUTED: return item
    if item.status!=DestructionRequest.Status.APPROVED or item.target_model!="Attachment" or item.target_id!=str(attachment.pk): raise ValidationError("승인된 해당 파일 파기 요청이 필요합니다.")
    if LegalHold.objects.filter(target_model="Attachment",target_id=str(attachment.pk),status=LegalHold.Status.APPROVED).exists() or attachment.legal_hold: raise ValidationError("legal hold 대상 파일은 파기할 수 없습니다.")
    if not attachment.destroyed_at:
        attachment.file.delete(save=False); attachment.destroyed_at=timezone.now(); attachment.is_deleted=True; attachment.save(update_fields=["destroyed_at","is_deleted"])
    item.status=DestructionRequest.Status.EXECUTED; item.executed_at=attachment.destroyed_at; item.evidence={"sha256":attachment.sha256,"destroyed_at":attachment.destroyed_at.isoformat()}; item.save(); record_audit(user=user,action="DESTRUCTION_EXECUTE",target=item,after=item.evidence,reason=item.reason,request=request,require_reason=True); return item
