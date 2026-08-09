from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.approvals.models import Approval
from apps.audit.services import record_audit, snapshot

FLOW={"RECEIVED":"UNDER_REVIEW","UNDER_REVIEW":"INVESTIGATING","INVESTIGATING":"CAPA_IN_PROGRESS","CAPA_IN_PROGRESS":"APPROVAL_PENDING","APPROVAL_PENDING":"REPORTING","REPORTING":"CLOSED"}
@transaction.atomic
def transition_event(event,new_status,user,comment="",request=None):
    if new_status not in {FLOW.get(event.status),"ON_HOLD","REJECTED"}: raise ValidationError("허용되지 않는 상태 전환입니다.")
    if user.role=="STAFF": raise PermissionDenied("STAFF는 상태를 변경할 수 없습니다.")
    if new_status in {"REJECTED","CLOSED"} and not comment.strip(): raise ValidationError("반려 또는 종료 사유가 필요합니다.")
    if new_status=="APPROVAL_PENDING":
        if not hasattr(event,"investigation") or not event.capas.exists(): raise ValidationError("조사와 CAPA가 있어야 승인 요청할 수 있습니다.")
        if event.capas.exclude(status__in=["COMPLETED","CLOSED"]).exists(): raise ValidationError("모든 CAPA가 완료되어야 승인 요청할 수 있습니다.")
    if new_status=="CLOSED":
        if user.role!="ADMIN": raise PermissionDenied("ADMIN만 종료할 수 있습니다.")
        if not event.approvals.filter(decision="APPROVED").exists(): raise ValidationError("승인되지 않은 건은 종료할 수 없습니다.")
        if event.capas.exclude(status="CLOSED").exists(): raise ValidationError("모든 CAPA가 종료되어야 합니다.")
        if event.reports.exists() and event.reports.exclude(report_status="SUBMITTED").exists(): raise ValidationError("모든 규제 보고서가 제출되어야 합니다.")
    before=snapshot(event); event.status=new_status; event.save(update_fields=["status","updated_at"])
    record_audit(user=user,action="STATUS_CHANGE",target=event,before=before,after=snapshot(event),reason=comment,request=request,require_reason=new_status in {"REJECTED","CLOSED"})
    return event
@transaction.atomic
def request_approval(event,user,approver,request=None):
    transition_event(event,"APPROVAL_PENDING",user,request=request); approval=Approval.objects.create(adverse_event=event,requested_by=user,approver=approver)
    record_audit(user=user,action="APPROVAL_REQUEST",target=approval,after=snapshot(approval),reason="승인 요청",request=request); return approval
