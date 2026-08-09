from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.adverse_events.models import AdverseEvent, validate_attachment
from apps.adverse_events.services import transition_event
from apps.approvals.models import Approval
from apps.audit.models import AuditLog
from apps.capa.models import CAPA
from apps.devices.models import DeviceLot, MedicalDevice
from apps.reports.services import approve_report, create_report_from_event, generate_docx_report, request_report_review

pytestmark=pytest.mark.django_db
@pytest.fixture
def users(): return {r:User.objects.create_user(r.lower(),password="Pass1234!",role=r) for r in ("ADMIN","RA_QA","STAFF")}
@pytest.fixture
def event(users):
    d=MedicalDevice.objects.create(device_code="D1",product_name="Device",model_name="M1",manufacturer="Maker",product_category="Monitor",approval_number="A1",risk_class="II")
    lot=DeviceLot.objects.create(medical_device=d,lot_number="L1",serial_number="S1",manufacture_date=timezone.localdate())
    return AdverseEvent.objects.create(title="Event",description="Description",medical_device=d,device_lot=lot,reporter=users["STAFF"],assigned_to=users["RA_QA"],occurred_at=timezone.now(),event_location="Hospital",severity="HIGH",event_type="Failure",due_date=timezone.localdate()+timedelta(days=5))
def test_login_success(client,users): assert client.login(username="staff",password="Pass1234!")
def test_login_failure(client,users): assert not client.login(username="staff",password="wrong")
@pytest.mark.parametrize("path",["dashboard","event_list","event_create","devices","capas"])
def test_login_required(client,path): assert client.get(reverse(path)).status_code==302
def test_dashboard_staff(client,users): client.force_login(users["STAFF"]); assert client.get(reverse("dashboard")).status_code==200
def test_audit_admin_only(client,users): client.force_login(users["STAFF"]); assert client.get(reverse("audits")).status_code==302
def test_audit_admin(client,users): client.force_login(users["ADMIN"]); assert client.get(reverse("audits")).status_code==200
def test_event_number(event): assert event.event_number.startswith(f"AE-{timezone.localdate().year}-") and len(event.event_number)==14
def test_deadline_normal(event): assert event.deadline_label=="7일 이내"
def test_deadline_three_days(event): event.due_date=timezone.localdate()+timedelta(days=2); assert event.deadline_label=="3일 이내"
def test_deadline_today(event): event.due_date=timezone.localdate(); assert event.deadline_label=="오늘 마감"
def test_deadline_overdue(event): event.due_date=timezone.localdate()-timedelta(days=1); event.save(); assert event.is_overdue and event.deadline_label=="기한 초과"
def test_invalid_transition(event,users):
    with pytest.raises(ValidationError): transition_event(event,"CLOSED",users["ADMIN"])
def test_staff_transition_denied(event,users):
    with pytest.raises(PermissionDenied): transition_event(event,"UNDER_REVIEW",users["STAFF"])
def test_valid_review_transition(event,users): transition_event(event,"UNDER_REVIEW",users["RA_QA"]); assert event.status=="UNDER_REVIEW"
def test_approval_requires_investigation(event,users):
    event.status="CAPA_IN_PROGRESS"; event.save()
    with pytest.raises(ValidationError): transition_event(event,"APPROVAL_PENDING",users["RA_QA"])
def test_close_requires_approval(event,users):
    event.status="REPORTING"; event.save()
    with pytest.raises(ValidationError): transition_event(event,"CLOSED",users["ADMIN"])
def test_close_admin(event,users):
    event.status="REPORTING"; event.save(); Approval.objects.create(adverse_event=event,requested_by=users["RA_QA"],approver=users["ADMIN"],decision="APPROVED"); transition_event(event,"CLOSED",users["ADMIN"],comment="종료 조건 충족"); assert event.status=="CLOSED"
def test_capa_number(event,users):
    c=CAPA.objects.create(adverse_event=event,capa_type="BOTH",issue_description="i",corrective_action="c",preventive_action="p",owner=users["RA_QA"],planned_completion_date=timezone.localdate()); assert c.capa_number.startswith("CAPA-")
def test_capa_update(event,users):
    c=CAPA.objects.create(adverse_event=event,capa_type="BOTH",issue_description="i",corrective_action="c",preventive_action="p",owner=users["RA_QA"],planned_completion_date=timezone.localdate()); c.status="COMPLETED"; c.save(); assert CAPA.objects.get(pk=c.pk).status=="COMPLETED"
def test_bad_extension():
    with pytest.raises(ValidationError): validate_attachment(SimpleUploadedFile("x.exe",b"x"))
def test_good_extension(): validate_attachment(SimpleUploadedFile("x.pdf",b"%PDF-1.7\n",content_type="application/pdf"))
def test_large_file():
    f=SimpleUploadedFile("x.pdf",b"x"); f.size=20*1024*1024+1
    with pytest.raises(ValidationError): validate_attachment(f)
def test_audit_created(event,users): transition_event(event,"UNDER_REVIEW",users["RA_QA"]); assert AuditLog.objects.filter(object_id=str(event.pk)).exists()
def test_api_auth(client): assert client.get("/api/events/").status_code in (401,403)
def test_api_staff_scope(client,event,users): client.force_login(users["STAFF"]); assert client.get("/api/events/").json()[0]["id"]==event.id
def test_csv(client,event,users): client.force_login(users["RA_QA"]); assert client.get(reverse("event_list")+"?format=csv").status_code==200
def test_docx(event,users,tmp_path,settings):
    settings.MEDIA_ROOT=tmp_path; r=create_report_from_event(event,users["RA_QA"],regulatory_authority="내부",report_type="INTERNAL"); request_report_review(r,users["RA_QA"]); approve_report(r,users["ADMIN"],password="Pass1234!",reason="검토 완료"); p=generate_docx_report(r,users["RA_QA"]); assert p.exists() and p.suffix==".docx"
