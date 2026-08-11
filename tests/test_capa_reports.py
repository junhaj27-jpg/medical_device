from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.adverse_events.models import AdverseEvent, PatientAnonymousInfo
from apps.audit.models import AuditLog
from apps.capa.services import change_capa_status, close_capa, create_capa, reopen_capa
from apps.devices.models import DeviceLot, MedicalDevice
from apps.investigations.models import Investigation
from apps.reports.services import (
    approve_report,
    create_report_from_event,
    generate_docx_report,
    mark_report_submitted,
    populate_report_fields,
    request_report_review,
)

pytestmark=pytest.mark.django_db

@pytest.fixture
def data():
    admin=User.objects.create_user("admin2",password="Pass1234!",role="ADMIN"); ra=User.objects.create_user("ra2",password="Pass1234!",role="RA_QA"); staff=User.objects.create_user("staff2",password="Pass1234!",role="STAFF")
    d=MedicalDevice.objects.create(device_code="T-1",product_name="Monitor",model_name="M",manufacturer="Maker",product_category="Monitoring",approval_number="A",risk_class="II")
    lot=DeviceLot.objects.create(medical_device=d,lot_number="L",serial_number="S",manufacture_date=timezone.localdate())
    e=AdverseEvent.objects.create(title="Event",description="Desc",medical_device=d,device_lot=lot,reporter=staff,assigned_to=ra,occurred_at=timezone.now(),event_location="Hospital",severity="HIGH",event_type="Failure",due_date=timezone.localdate()+timedelta(days=10))
    PatientAnonymousInfo.objects.create(adverse_event=e,anonymous_code="P1",age_group="adult",gender="unknown")
    return admin,ra,staff,e
def add_investigation(e,ra): return Investigation.objects.create(adverse_event=e,investigator=ra,investigation_summary="Summary",root_cause="Cause",investigation_method="Test",started_at=timezone.now())
def capa_kwargs(e,ra): return {"adverse_event":e,"capa_type":"CORRECTIVE_PREVENTIVE","issue_description":"Issue","root_cause":"Cause","corrective_action":"Fix","preventive_action":"Prevent","action_plan":"Plan","owner":ra,"planned_start_date":timezone.localdate(),"planned_completion_date":timezone.localdate()+timedelta(days=10),"completion_percentage":0}
def test_capa_number(data): admin,ra,staff,e=data; add_investigation(e,ra); assert create_capa(ra,**capa_kwargs(e,ra)).capa_number.startswith("CAPA-")
def test_capa_unique(data): admin,ra,staff,e=data; add_investigation(e,ra); a=create_capa(ra,**capa_kwargs(e,ra)); b=create_capa(ra,**capa_kwargs(e,ra)); assert a.capa_number!=b.capa_number
def test_staff_cannot_create(data): admin,ra,staff,e=data; add_investigation(e,ra); pytest.raises(PermissionDenied,create_capa,staff,**capa_kwargs(e,ra))
def test_requires_investigation(data): admin,ra,staff,e=data; pytest.raises(ValidationError,create_capa,ra,**capa_kwargs(e,ra))
def test_plan_dates(data): admin,ra,staff,e=data; add_investigation(e,ra); kw=capa_kwargs(e,ra); kw["planned_completion_date"]=timezone.localdate()-timedelta(days=1); pytest.raises(ValidationError,create_capa,ra,**kw)
def test_completion_requires_100(data): admin,ra,staff,e=data; add_investigation(e,ra); c=create_capa(ra,**capa_kwargs(e,ra)); change_capa_status(c,"IN_PROGRESS",ra); change_capa_status(c,"REVIEW_PENDING",ra); pytest.raises(ValidationError,change_capa_status,c,"COMPLETED",ra)
def test_completion_requires_date(data): admin,ra,staff,e=data; add_investigation(e,ra); kw=capa_kwargs(e,ra); kw["completion_percentage"]=100; c=create_capa(ra,**kw); change_capa_status(c,"IN_PROGRESS",ra); change_capa_status(c,"REVIEW_PENDING",ra); pytest.raises(ValidationError,change_capa_status,c,"COMPLETED",ra)
def test_close_requires_effectiveness(data): admin,ra,staff,e=data; add_investigation(e,ra); c=create_capa(ra,**capa_kwargs(e,ra)); pytest.raises(ValidationError,close_capa,c,admin)
def test_capa_overdue(data): admin,ra,staff,e=data; add_investigation(e,ra); kw=capa_kwargs(e,ra); kw["planned_start_date"]=timezone.localdate()-timedelta(days=2); kw["planned_completion_date"]=timezone.localdate()-timedelta(days=1); assert create_capa(ra,**kw).is_overdue
def test_capa_audit(data): admin,ra,staff,e=data; add_investigation(e,ra); c=create_capa(ra,**capa_kwargs(e,ra)); change_capa_status(c,"IN_PROGRESS",ra); assert AuditLog.objects.filter(action="CAPA_STATUS").exists()
def test_reopen_admin_only(data): admin,ra,staff,e=data; add_investigation(e,ra); c=create_capa(ra,**capa_kwargs(e,ra)); c.status="CLOSED"; c.save(); pytest.raises(PermissionDenied,reopen_capa,c,ra)
def test_report_number(data): admin,ra,staff,e=data; r=create_report_from_event(e,ra,regulatory_authority="MFDS"); assert r.report_number.startswith("RPT-")
def test_report_population(data): admin,ra,staff,e=data; fields=populate_report_fields(e); assert "Monitor" in fields["device_information"] and "Event" in fields["event_summary"]
def test_staff_report_denied(data): admin,ra,staff,e=data; pytest.raises(PermissionDenied,create_report_from_event,e,staff,regulatory_authority="MFDS")
def test_approval_admin_only(data): admin,ra,staff,e=data; r=create_report_from_event(e,ra,regulatory_authority="MFDS"); pytest.raises(PermissionDenied,approve_report,r,ra)
def test_draft_cannot_be_approved(data): admin,ra,staff,e=data; r=create_report_from_event(e,ra,regulatory_authority="MFDS"); pytest.raises(ValidationError,approve_report,r,admin)
def test_submit_before_approval(data): admin,ra,staff,e=data; r=create_report_from_event(e,ra,regulatory_authority="MFDS"); pytest.raises(ValidationError,mark_report_submitted,r,ra)
def test_submit_records_user(data,tmp_path,settings): admin,ra,staff,e=data; settings.MEDIA_ROOT=tmp_path; r=create_report_from_event(e,ra,regulatory_authority="MFDS"); request_report_review(r,ra); generate_docx_report(r,ra); approve_report(r,admin,password="Pass1234!",reason="검토 완료"); mark_report_submitted(r,ra); assert r.submitted_by==ra and r.submitted_at
def test_submitted_cannot_return_to_review(data,tmp_path,settings): admin,ra,staff,e=data; settings.MEDIA_ROOT=tmp_path; r=create_report_from_event(e,ra,regulatory_authority="MFDS"); request_report_review(r,ra); generate_docx_report(r,ra); approve_report(r,admin,password="Pass1234!",reason="검토 완료"); mark_report_submitted(r,ra); pytest.raises(ValidationError,request_report_review,r,ra)
def test_rejected_cannot_be_submitted(data): admin,ra,staff,e=data; r=create_report_from_event(e,ra,regulatory_authority="MFDS"); r.report_status="REJECTED"; r.save(); pytest.raises(ValidationError,mark_report_submitted,r,ra)
def test_report_overdue(data): admin,ra,staff,e=data; r=create_report_from_event(e,ra,regulatory_authority="MFDS",submission_due_date=timezone.localdate()-timedelta(days=1)); assert r.is_overdue
def test_docx_version_and_filename(data,tmp_path,settings): admin,ra,staff,e=data; settings.MEDIA_ROOT=tmp_path; r=create_report_from_event(e,ra,regulatory_authority="MFDS"); request_report_review(r,ra); p=generate_docx_report(r,ra); approve_report(r,admin,password="Pass1234!",reason="검토 완료"); assert p.name.endswith("_v1.docx") and r.document_version==1 and p.exists()

def test_capa_allowed_status_flow(data):
    admin,ra,staff,e=data; add_investigation(e,ra); kw=capa_kwargs(e,ra); kw.update(completion_percentage=100,actual_completion_date=timezone.localdate(),effectiveness_review="OK",effectiveness_result="EFFECTIVE")
    c=create_capa(ra,**kw)
    for status in ("IN_PROGRESS","REVIEW_PENDING","COMPLETED","CLOSED"): change_capa_status(c,status,admin)
    assert c.status == "CLOSED"

def test_capa_blocks_skips_and_reverse_transitions(data):
    admin,ra,staff,e=data; add_investigation(e,ra); c=create_capa(ra,**capa_kwargs(e,ra))
    with pytest.raises(ValidationError): change_capa_status(c,"REVIEW_PENDING",ra)
    change_capa_status(c,"IN_PROGRESS",ra)
    with pytest.raises(ValidationError): change_capa_status(c,"DRAFT",ra)
@pytest.mark.parametrize("name",["capa:create","reports:create"])
def test_staff_url_denied(client,data,name): admin,ra,staff,e=data; client.force_login(staff); assert client.get(reverse(name)).status_code==403
@pytest.mark.parametrize("name",["capa:list","reports:list"])
def test_list_login_required(client,name): assert client.get(reverse(name)).status_code==302

