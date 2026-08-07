from pathlib import Path

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def account():
    return User.objects.create_user(username="security-user", password="Initial!Pass9", role="STAFF")


def password_payload(old="Initial!Pass9", new="Changed!Pass9"):
    return {"old_password": old, "new_password1": new, "new_password2": new}


def test_password_change_requires_login(client):
    response = client.get(reverse("password_change"))
    assert response.status_code == 302
    assert response.url.startswith(f"{reverse('login')}?next=")


def test_wrong_current_password_does_not_change_password(client, account):
    client.force_login(account)
    response = client.post(reverse("password_change"), password_payload(old="Wrong!Pass99"))
    account.refresh_from_db()
    assert response.status_code == 200
    assert account.check_password("Initial!Pass9")


def test_weak_password_is_rejected(client, account):
    client.force_login(account)
    response = client.post(reverse("password_change"), password_payload(new="weakpassword"))
    account.refresh_from_db()
    assert response.status_code == 200
    assert "영문 대문자" in response.content.decode()
    assert account.check_password("Initial!Pass9")


def test_password_confirmation_mismatch_is_rejected(client, account):
    client.force_login(account)
    data = password_payload()
    data["new_password2"] = "Different!Pass9"
    response = client.post(reverse("password_change"), data)
    account.refresh_from_db()
    assert response.status_code == 200
    assert account.check_password("Initial!Pass9")


def test_successful_change_updates_credentials_keeps_session_and_audits(client, account):
    client.force_login(account)
    response = client.post(reverse("password_change"), password_payload())
    assert response.status_code == 302
    assert response.url == reverse("password_change_done")
    account.refresh_from_db()
    assert account.check_password("Changed!Pass9")
    assert not account.check_password("Initial!Pass9")
    assert client.get(reverse("dashboard")).status_code == 200
    assert client.login(username=account.username, password="Changed!Pass9")
    assert not client.login(username=account.username, password="Initial!Pass9")
    audit = AuditLog.objects.get(action="PASSWORD_CHANGED", user=account)
    assert audit.after_data == {"event": "비밀번호 변경 완료"}
    assert "password" not in str(audit.before_data).lower()
    assert "password" not in str(audit.after_data).lower()


def test_seed_rerun_does_not_change_existing_password(monkeypatch):
    existing = User.objects.create_user(username="admin", password="Existing!Pass9", role="ADMIN")
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "Unused!Admin9")
    monkeypatch.setenv("DEMO_RA_PASSWORD", "Created!RaPass9")
    monkeypatch.setenv("DEMO_STAFF_PASSWORD", "Created!Staff9")
    call_command("seed_demo_data")
    existing.refresh_from_db()
    assert existing.check_password("Existing!Pass9")
    call_command("seed_demo_data")
    existing.refresh_from_db()
    assert existing.check_password("Existing!Pass9")


def test_public_files_do_not_expose_demo_passwords():
    root = Path(__file__).resolve().parents[1]
    login = (root / "templates" / "login.html").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    seed = (root / "apps" / "adverse_events" / "management" / "commands" / "seed_demo_data.py").read_text(encoding="utf-8")
    assert "테스트 계정" not in login
    assert "| 사용자 | 비밀번호 |" not in readme
    assert "DEMO_ADMIN_PASSWORD" in readme
    assert "os.environ[env_name]" in seed
