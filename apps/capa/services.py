from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from apps.audit.models import AuditLog
from .models import CAPA


def _allowed(user):
    if user.role not in {"RA_QA", "ADMIN"}: raise PermissionDenied("RA·QA 또는 ADMIN만 CAPA를 변경할 수 있습니다.")


def _audit(user, action, capa, before=None, request=None):
    AuditLog.objects.create(user=user, action=action, model_name="CAPA", object_id=str(capa.pk), object_repr=capa.capa_number, before_data=before or {}, after_data={"status": capa.status, "progress": capa.completion_percentage}, ip_address=request.META.get("REMOTE_ADDR") if request else None)


def generate_capa_number():
    year=timezone.localdate().year; last=CAPA.objects.filter(capa_number__startswith=f"CAPA-{year}-").order_by("capa_number").last()
    return f"CAPA-{year}-{(int(last.capa_number[-6:])+1 if last else 1):06d}"


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
    _allowed(user); before={"status":capa.status,"progress":capa.completion_percentage}
    for key,value in data.items(): setattr(capa,key,value)
    _validate(capa); capa.save(); _audit(user,"CAPA_UPDATE",capa,before); return capa


def validate_capa_completion(capa):
    if not capa.actual_completion_date: raise ValidationError("완료 처리에는 실제 완료일이 필요합니다.")
    if capa.completion_percentage != 100: raise ValidationError("완료 처리에는 진행률 100%가 필요합니다.")


def change_capa_status(capa, new_status, user, request=None):
    _allowed(user); before={"status":capa.status}
    if capa.status==CAPA.Status.CLOSED and new_status!=CAPA.Status.IN_PROGRESS: raise ValidationError("종료 CAPA는 다시 열기만 가능합니다.")
    if new_status==CAPA.Status.COMPLETED: validate_capa_completion(capa)
    if new_status==CAPA.Status.CLOSED and (not capa.effectiveness_review or capa.effectiveness_result==CAPA.Effectiveness.NOT_REVIEWED): raise ValidationError("효과성 평가 후 종료할 수 있습니다.")
    capa.status=new_status; capa.save(update_fields=["status","updated_at"]); _audit(user,"CAPA_STATUS",capa,before,request); return capa


def close_capa(capa,user,request=None): return change_capa_status(capa,CAPA.Status.CLOSED,user,request)
def reopen_capa(capa,user,request=None):
    if user.role!="ADMIN": raise PermissionDenied("ADMIN만 CAPA를 다시 열 수 있습니다.")
    return change_capa_status(capa,CAPA.Status.IN_PROGRESS,user,request)
def calculate_capa_overdue_status(capa): return capa.is_overdue
