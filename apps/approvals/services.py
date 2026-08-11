import hashlib
import hmac
import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_audit, sanitize

from .models import ElectronicSignature, SignatureRevocation

SIGNATURE_FIELDS = {
    "RegulatoryReport": ["report_number","report_status","title","event_summary","device_information","patient_information","investigation_summary","root_cause_summary","capa_summary","conclusion","document_version","created_by"],
    "CAPA": ["capa_number","status","approval_status","approval_version","issue_description","root_cause","corrective_action","preventive_action","action_plan","owner","reviewer","completion_percentage","effectiveness_review","effectiveness_result"],
    "Investigation": ["status","approval_status","approval_version","investigation_summary","root_cause","investigation_method","evidence","investigator","completed_at"],
}


def _key():
    value=settings.SIGNATURE_HMAC_KEY
    if not value and settings.DEBUG: value=settings.SECRET_KEY
    if not value: raise ImproperlyConfigured("SIGNATURE_HMAC_KEY가 필요합니다.")
    return value.encode()


def canonical_snapshot(target):
    fields=SIGNATURE_FIELDS.get(target.__class__.__name__)
    if not fields: raise ValidationError("전자서명 대상이 아닙니다.")
    data={field: getattr(target, f"{field}_id", None) if hasattr(target, f"{field}_id") else getattr(target,field) for field in fields}
    return sanitize(data)


def _json(data): return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _hmac(data): return hmac.new(_key(),_json(data),hashlib.sha256).hexdigest()


def _lock_target(target):
    locked=target.__class__.objects.select_for_update().get(pk=target.pk)
    target.__dict__.update(locked.__dict__)
    return target


@transaction.atomic
def sign_approval(*,target,user,password,meaning,reason,request=None,allowed_roles=("ADMIN",),forbid_self_user_id=None):
    target=_lock_target(target)
    if user.role not in allowed_roles: raise PermissionDenied("이 승인 단계에 대한 권한이 없습니다.")
    if forbid_self_user_id and user.pk==forbid_self_user_id: raise PermissionDenied("작성자는 자신의 기록을 승인할 수 없습니다.")
    if not password or not user.check_password(password): raise ValidationError("승인자 재인증에 실패했습니다.")
    if not reason.strip(): raise ValidationError("승인 사유 또는 의견이 필요합니다.")
    canonical=canonical_snapshot(target); data_hash=hashlib.sha256(_json(canonical)).hexdigest()
    previous=ElectronicSignature.objects.filter(target_model=target.__class__.__name__,target_id=str(target.pk)).order_by("id").last()
    signed_at=timezone.now(); payload={"signer_id":user.pk,"signer_role":user.role,"meaning":meaning,"reason":reason,"signed_at":signed_at.isoformat(),"target_model":target.__class__.__name__,"target_id":str(target.pk),"target_version":getattr(target,"document_version",1),"data_hash":data_hash,"previous_hash":previous.current_hash if previous else "","schema_version":1}
    signature=ElectronicSignature.objects.create(signer=user,signer_display_name=user.get_full_name() or user.username,signer_role=user.role,meaning=meaning,reason=reason,target_model=payload["target_model"],target_id=payload["target_id"],target_version=payload["target_version"],canonical_data=canonical,data_hash=data_hash,previous_hash=payload["previous_hash"],current_hash=_hmac(payload),signed_at=signed_at)
    record_audit(user=user,action="ELECTRONIC_SIGNATURE",target=signature,after=payload,reason=reason,request=request,require_reason=True)
    return signature


def verify_signature(signature):
    canonical_hash=hashlib.sha256(_json(signature.canonical_data)).hexdigest()
    payload={"signer_id":signature.signer_id,"signer_role":signature.signer_role,"meaning":signature.meaning,"reason":signature.reason,"signed_at":signature.signed_at.isoformat(),"target_model":signature.target_model,"target_id":signature.target_id,"target_version":signature.target_version,"data_hash":signature.data_hash,"previous_hash":signature.previous_hash,"schema_version":signature.schema_version}
    return canonical_hash==signature.data_hash and hmac.compare_digest(signature.current_hash,_hmac(payload)) and not hasattr(signature,"revocation")


def verify_signature_chain(target):
    previous=""
    for signature in ElectronicSignature.objects.filter(target_model=target.__class__.__name__,target_id=str(target.pk)).order_by("id"):
        if signature.previous_hash!=previous or not verify_signature(signature): return False
        previous=signature.current_hash
    return True


@transaction.atomic
def revoke_active_signatures(target, *, user, reason, request=None):
    signatures=ElectronicSignature.objects.filter(target_model=target.__class__.__name__,target_id=str(target.pk),revocation__isnull=True)
    for signature in signatures:
        revocation=SignatureRevocation.objects.create(signature=signature,revoked_by=user,reason=reason)
        record_audit(user=user,action="SIGNATURE_REVOKED",target=revocation,after={"signature_id":signature.pk},reason=reason,request=request,require_reason=True)


@transaction.atomic
def approve_capa(capa, *, user, password, reason, request=None):
    capa=_lock_target(capa)
    if capa.approval_status!="REVIEW_PENDING": raise ValidationError("검토 대기 CAPA만 승인할 수 있습니다.")
    signature=sign_approval(target=capa,user=user,password=password,meaning="CAPA 승인",reason=reason,request=request,forbid_self_user_id=capa.created_by_id); capa.approval_status="APPROVED"; capa.save(update_fields=["approval_status","updated_at"]); record_audit(user=user,action="CAPA_APPROVE",target=capa,reason=reason,request=request,require_reason=True); return signature


@transaction.atomic
def approve_investigation(investigation, *, user, password, reason, request=None):
    investigation=_lock_target(investigation)
    if investigation.approval_status!="REVIEW_PENDING": raise ValidationError("검토 대기 조사만 승인할 수 있습니다.")
    signature=sign_approval(target=investigation,user=user,password=password,meaning="조사 결과 승인",reason=reason,request=request,forbid_self_user_id=investigation.investigator_id)
    investigation.approval_status="APPROVED"; investigation.save(update_fields=["approval_status","updated_at"]); record_audit(user=user,action="INVESTIGATION_APPROVE",target=investigation,reason=reason,request=request,require_reason=True)
    return signature

@transaction.atomic
def request_signature_review(target,*,user,request=None):
    if user.role not in {"RA_QA","ADMIN"}: raise PermissionDenied("검토 요청 권한이 없습니다.")
    if target.approval_status not in {"DRAFT","REJECTED","NEEDS_REAPPROVAL"}: raise ValidationError("현재 상태에서는 검토 요청할 수 없습니다.")
    target.approval_status="REVIEW_PENDING"; target.save(update_fields=["approval_status","updated_at"]); record_audit(user=user,action=f"{target.__class__.__name__.upper()}_REVIEW_REQUEST",target=target,reason="전자서명 검토 요청",request=request); return target

@transaction.atomic
def reject_signature_target(target,*,user,password,reason,request=None):
    target=_lock_target(target)
    if target.approval_status!="REVIEW_PENDING": raise ValidationError("검토 대기 기록만 반려할 수 있습니다.")
    creator_id=target.created_by_id if target.__class__.__name__=="CAPA" else target.investigator_id
    signature=sign_approval(target=target,user=user,password=password,meaning=f"{target.__class__.__name__} 반려",reason=reason,request=request,forbid_self_user_id=creator_id); target.approval_status="REJECTED"; target.save(update_fields=["approval_status","updated_at"]); record_audit(user=user,action=f"{target.__class__.__name__.upper()}_REJECT",target=target,reason=reason,request=request,require_reason=True); return signature

