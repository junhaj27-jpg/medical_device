from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.approvals.models import ElectronicSignature
from apps.approvals.services import revoke_active_signatures
from apps.audit.services import record_audit, snapshot

from .models import CAPA

CAPA_STATUS_TRANSITIONS = {
    CAPA.Status.DRAFT: {CAPA.Status.IN_PROGRESS, CAPA.Status.CANCELLED},
    CAPA.Status.IN_PROGRESS: {CAPA.Status.REVIEW_PENDING, CAPA.Status.CANCELLED},
    CAPA.Status.REVIEW_PENDING: {CAPA.Status.COMPLETED, CAPA.Status.CANCELLED},
    CAPA.Status.COMPLETED: {CAPA.Status.CLOSED},
    CAPA.Status.CLOSED: set(),
    CAPA.Status.CANCELLED: set(),
}


def visible_capas(user):
    qs = CAPA.objects.all()
    return qs.filter(adverse_event__reporter=user) if user.role == "STAFF" else qs


def _allowed(user):
    if user.role not in {"RA_QA", "ADMIN"}: raise PermissionDenied("RA·QA 또는 ADMIN만 CAPA를 변경할 수 있습니다.")


def _audit(user, action, capa, before=None, request=None):
    record_audit(user=user,action=action,target=capa,before=before or {},after=snapshot(capa),request=request)


def generate_capa_number():
    from apps.compliance.services import next_management_number
    return next_management_number("CAPA")


def _validate(capa):
    if capa.planned_completion_date < capa.planned_start_date: raise ValidationError("계획 완료일은 계획 시작일보다 빠를 수 없습니다.")
    if capa.actual_start_date and capa.actual_completion_date and capa.actual_completion_date < capa.actual_start_date: raise ValidationError("실제 완료일은 실제 시작일보다 빠를 수 없습니다.")
    if not 0 <= capa.completion_percentage <= 100: raise ValidationError("진행률은 0~100이어야 합니다.")


@transaction.atomic
def create_capa(user, **data):
    _allowed(user); event=data["adverse_event"]
    if not hasattr(event, "investigation"): raise ValidationError("조사 내용이 있어야 CAPA를 생성할 수 있습니다.")
    capa=CAPA(created_by=user, **data); _validate(capa); capa.save(); _audit(user,"CAPA_CREATE",capa); return capa


@transaction.atomic
def update_capa(capa, user, **data):
    _allowed(user); before=snapshot(capa)
    if "status" in data: raise ValidationError("CAPA 상태는 상태 변경 서비스를 통해서만 변경할 수 있습니다.")
    for key,value in data.items(): setattr(capa,key,value)
    _validate(capa)
    if ElectronicSignature.objects.filter(target_model="CAPA",target_id=str(capa.pk),revocation__isnull=True).exists(): capa.approval_status=CAPA.ApprovalStatus.NEEDS_REAPPROVAL; capa.approval_version+=1
    revoke_active_signatures(capa,user=user,reason="서명 후 CAPA 중요 데이터 변경"); capa.save(); _audit(user,"CAPA_UPDATE",capa,before); return capa


def validate_capa_completion(capa):
    if not capa.actual_completion_date: raise ValidationError("완료 처리에는 실제 완료일이 필요합니다.")
    if capa.completion_percentage != 100: raise ValidationError("완료 처리에는 진행률 100%가 필요합니다.")


def change_capa_status(capa, new_status, user, request=None):
    _allowed(user); before={"status":capa.status}
    if new_status not in CAPA.Status.values: raise ValidationError("알 수 없는 CAPA 상태입니다.")
    if new_status not in CAPA_STATUS_TRANSITIONS[capa.status]:
        raise ValidationError(f"CAPA 상태를 {capa.status}에서 {new_status}(으)로 변경할 수 없습니다.")
    if new_status==CAPA.Status.COMPLETED: validate_capa_completion(capa)
    if new_status==CAPA.Status.CLOSED and (not capa.effectiveness_review or capa.effectiveness_result==CAPA.Effectiveness.NOT_REVIEWED): raise ValidationError("효과성 평가 후 종료할 수 있습니다.")
    capa.status=new_status; capa.save(update_fields=["status","updated_at"]); _audit(user,"CAPA_STATUS",capa,before,request); return capa


def close_capa(capa,user,request=None): return change_capa_status(capa,CAPA.Status.CLOSED,user,request)
def reopen_capa(capa,user,request=None):
    if user.role!="ADMIN": raise PermissionDenied("ADMIN만 CAPA를 다시 열 수 있습니다.")
    if capa.status != CAPA.Status.CLOSED: raise ValidationError("종료된 CAPA만 다시 열 수 있습니다.")
    before={"status":capa.status}; capa.status=CAPA.Status.IN_PROGRESS
    capa.save(update_fields=["status","updated_at"]); _audit(user,"CAPA_REOPEN",capa,before,request); return capa
def calculate_capa_overdue_status(capa): return capa.is_overdue
