from django.core.exceptions import PermissionDenied,ValidationError
from apps.audit.models import AuditLog
from apps.approvals.models import Approval
FLOW={"RECEIVED":"UNDER_REVIEW","UNDER_REVIEW":"INVESTIGATING","INVESTIGATING":"CAPA_IN_PROGRESS","CAPA_IN_PROGRESS":"APPROVAL_PENDING","APPROVAL_PENDING":"REPORTING","REPORTING":"CLOSED"}
def transition_event(event,new_status,user,comment=""):
    if new_status not in {FLOW.get(event.status),"ON_HOLD","REJECTED"}: raise ValidationError("허용되지 않는 상태 전환입니다.")
    if user.role=="STAFF": raise PermissionDenied("STAFF는 상태를 변경할 수 없습니다.")
    if new_status=="APPROVAL_PENDING":
        if not hasattr(event,"investigation") or not event.capas.exists(): raise ValidationError("조사와 CAPA가 있어야 승인 요청할 수 있습니다.")
        if event.capas.exclude(status__in=["COMPLETED","CLOSED"]).exists(): raise ValidationError("모든 CAPA가 완료되어야 승인 요청할 수 있습니다.")
    if new_status=="CLOSED":
        if user.role!="ADMIN": raise PermissionDenied("ADMIN만 종료할 수 있습니다.")
        if not event.approvals.filter(decision="APPROVED").exists(): raise ValidationError("승인되지 않은 건은 종료할 수 없습니다.")
        if event.capas.exclude(status="CLOSED").exists(): raise ValidationError("모든 CAPA가 종료되어야 합니다.")
        if event.reports.exists() and event.reports.exclude(report_status="SUBMITTED").exists(): raise ValidationError("모든 규제 보고서가 제출되어야 합니다.")
    before=event.status; event.status=new_status; event.save(update_fields=["status","updated_at"])
    AuditLog.objects.create(user=user,action="STATUS_CHANGE",model_name="AdverseEvent",object_id=str(event.pk),object_repr=event.event_number,before_data={"status":before},after_data={"status":new_status,"comment":comment})
    return event
def request_approval(event,user,approver):
    transition_event(event,"APPROVAL_PENDING",user); return Approval.objects.create(adverse_event=event,requested_by=user,approver=approver)
