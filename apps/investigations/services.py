from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.approvals.models import ElectronicSignature
from apps.approvals.services import revoke_active_signatures
from apps.audit.services import record_audit, snapshot


@transaction.atomic
def update_investigation(investigation,*,user,request=None,**data):
    if user.role not in {"RA_QA","ADMIN"}: raise PermissionDenied("조사 수정 권한이 없습니다.")
    before=snapshot(investigation)
    for key,value in data.items(): setattr(investigation,key,value)
    if ElectronicSignature.objects.filter(target_model="Investigation",target_id=str(investigation.pk),revocation__isnull=True).exists(): investigation.approval_status="NEEDS_REAPPROVAL"; investigation.approval_version+=1
    revoke_active_signatures(investigation,user=user,reason="서명 후 조사 중요 데이터 변경",request=request); investigation.save(); record_audit(user=user,action="INVESTIGATION_UPDATE",target=investigation,before=before,after=snapshot(investigation),reason="조사 내용 수정",request=request); return investigation
