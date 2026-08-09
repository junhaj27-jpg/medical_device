from datetime import timedelta
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.adverse_events.models import AdverseEvent
from apps.capa.models import CAPA
from apps.devices.models import DeviceLot, MedicalDevice
from apps.reports.models import RegulatoryReport

pytestmark = pytest.mark.django_db


def _event(reporter, code):
    device = MedicalDevice.objects.create(
        device_code=code,
        product_name=f"Device {code}",
        model_name="M",
        manufacturer="Maker",
        product_category="Monitor",
        approval_number=f"A-{code}",
        risk_class="II",
    )
    lot = DeviceLot.objects.create(
        medical_device=device,
        lot_number=f"L-{code}",
        manufacture_date=timezone.localdate(),
    )
    return AdverseEvent.objects.create(
        title=f"Event {code}",
        description="Description",
        medical_device=device,
        device_lot=lot,
        reporter=reporter,
        occurred_at=timezone.now(),
        event_location="Hospital",
        severity="HIGH",
        event_type="Failure",
        due_date=timezone.localdate() - timedelta(days=1),
    )


def test_staff_views_only_records_linked_to_own_events(client):
    staff = User.objects.create_user("scope-staff", password="Pass1234!", role="STAFF")
    other = User.objects.create_user("other-staff", password="Pass1234!", role="STAFF")
    ra = User.objects.create_user("scope-ra", password="Pass1234!", role="RA_QA")
    own_event = _event(staff, "OWN")
    other_event = _event(other, "OTHER")
    past = timezone.localdate() - timedelta(days=1)
    own_capa = CAPA.objects.create(adverse_event=own_event, issue_description="Own CAPA", owner=ra, planned_completion_date=past)
    other_capa = CAPA.objects.create(adverse_event=other_event, issue_description="Other CAPA", owner=ra, planned_completion_date=past)
    own_report = RegulatoryReport.objects.create(adverse_event=own_event, regulatory_authority="MFDS", title="Own report", created_by=ra, submission_due_date=past)
    other_report = RegulatoryReport.objects.create(adverse_event=other_event, regulatory_authority="MFDS", title="Other report", created_by=ra, submission_due_date=past)

    client.force_login(staff)
    dashboard = client.get(reverse("dashboard"))
    assert dashboard.context["stats"]["total"] == 1
    assert dashboard.context["stats"]["capa_overdue"] == 1
    assert dashboard.context["stats"]["report_overdue"] == 1
    assert list(dashboard.context["urgent_capas"]) == [own_capa]
    assert list(dashboard.context["urgent_reports"]) == [own_report]

    assert own_capa.capa_number.encode() in client.get(reverse("capa:list")).content
    assert other_capa.capa_number.encode() not in client.get(reverse("capa:list")).content
    assert own_report.report_number.encode() in client.get(reverse("reports:list")).content
    assert other_report.report_number.encode() not in client.get(reverse("reports:list")).content
    assert client.get(reverse("capa:detail", args=[other_capa.pk])).status_code == 404
    assert client.get(reverse("reports:detail", args=[other_report.pk])).status_code == 404
    device_page = client.get(reverse("devices")).content
    assert b"OWN" in device_page
    assert b"OTHER" not in device_page


def test_ra_and_admin_keep_global_visibility(client):
    staff = User.objects.create_user("global-staff", password="Pass1234!", role="STAFF")
    ra = User.objects.create_user("global-ra", password="Pass1234!", role="RA_QA")
    admin = User.objects.create_user("global-admin", password="Pass1234!", role="ADMIN")
    _event(staff, "GLOBAL")
    for user in (ra, admin):
        client.force_login(user)
        assert b"GLOBAL" in client.get(reverse("devices")).content


def test_docker_compose_uses_postgres_host_and_gunicorn():
    compose = (Path(__file__).resolve().parents[1] / "docker-compose.yml").read_text(encoding="utf-8")
    assert "POSTGRES_HOST: db" in compose
    assert "gunicorn config.wsgi:application --bind 0.0.0.0:8000" in compose
    assert "runserver" not in compose
