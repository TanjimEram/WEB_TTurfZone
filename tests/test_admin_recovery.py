"""Admin login lockout + forgot-password by email (M5.10, D-51)."""
import re
from datetime import timedelta

import pytest
from itsdangerous import TimestampSigner

from extensions import db
from models import Admin, LoginFailure
from models._time import utcnow
from tests.test_admin_routes import PASSWORD, USERNAME, admin_user, as_admin  # noqa: F401  (fixtures)

EMAIL = "Owner@Example.com"
NEW_PASSWORD = "a-brand-new-long-passphrase"
FORGOT_SENT = "If that address is on file, a reset link is on its way."
LOCKED = "Too many wrong sign-ins"


@pytest.fixture
def outbox(app, monkeypatch):
    """Capture emails instead of sending them; mail counts as configured."""
    sent = []
    monkeypatch.setattr("services.auth.send_email", lambda to, subject, body: sent.append((to, subject, body)))
    app.config.update(MAIL_SERVER="mail.example.test", MAIL_FROM="noreply@example.test")
    return sent


@pytest.fixture
def with_email(app, admin_user):  # noqa: F811
    admin = db.session.scalar(db.select(Admin))
    admin.email = EMAIL.lower()
    db.session.commit()
    return admin


def _login(client, password, ip="203.0.113.5"):
    return client.post("/admin/login", data={"username": USERNAME, "password": password},
                       environ_base={"REMOTE_ADDR": ip})


def _reset_link(outbox):
    return re.search(r"https?://\S+/admin/reset/\S+", outbox[-1][2]).group(0)


def _path(link):
    return "/admin/reset/" + link.rsplit("/admin/reset/", 1)[1]


# --- lockout ---------------------------------------------------------------

def test_five_wrong_passwords_lock_that_address_even_for_the_right_password(client, admin_user):  # noqa: F811
    for _ in range(5):
        assert "Invalid username or password." in _login(client, "wrong").get_data(as_text=True)
    resp = _login(client, PASSWORD)
    assert resp.status_code == 429
    assert LOCKED in resp.get_data(as_text=True)


def test_lockout_is_per_address(client, admin_user):  # noqa: F811
    for _ in range(5):
        _login(client, "wrong", ip="203.0.113.5")
    assert _login(client, PASSWORD, ip="198.51.100.7").status_code == 302


def test_failures_older_than_15_minutes_do_not_count(client, admin_user):  # noqa: F811
    old = utcnow() - timedelta(minutes=16)
    db.session.add_all([LoginFailure(ip="203.0.113.5", created_at=old) for _ in range(5)])
    db.session.commit()
    assert _login(client, PASSWORD).status_code == 302


def test_successful_login_clears_the_failure_count(app, admin_user):  # noqa: F811
    for _ in range(4):
        _login(app.test_client(), "wrong")
    assert _login(app.test_client(), PASSWORD).status_code == 302
    for _ in range(4):
        _login(app.test_client(), "wrong")
    assert _login(app.test_client(), PASSWORD).status_code == 302  # 4 + 4 would have locked it


# --- forgot password -------------------------------------------------------

def test_login_page_links_to_forgot(client):
    assert "/admin/forgot" in client.get("/admin/login").get_data(as_text=True)


def test_unknown_email_gets_the_same_message_and_no_email(client, with_email, outbox):
    resp = client.post("/admin/forgot", data={"email": "someone@else.test"})
    assert FORGOT_SENT in resp.get_data(as_text=True)
    assert outbox == []


def test_known_email_gets_username_and_link_on_the_fixed_site_url(app, client, with_email, outbox):
    app.config["SITE_URL"] = "https://tturfzone.example"
    resp = client.post("/admin/forgot", data={"email": "  OWNER@example.com "},
                       headers={"Host": "evil.example"})  # a forged Host must not reach the link
    assert FORGOT_SENT in resp.get_data(as_text=True)
    assert len(outbox) == 1
    to, _subject, body = outbox[0]
    assert to == EMAIL.lower()
    assert USERNAME in body
    assert _reset_link(outbox).startswith("https://tturfzone.example/admin/reset/")
    assert "evil.example" not in body


def test_second_request_within_5_minutes_sends_nothing(client, with_email, outbox):
    client.post("/admin/forgot", data={"email": EMAIL})
    resp = client.post("/admin/forgot", data={"email": EMAIL})
    assert FORGOT_SENT in resp.get_data(as_text=True)
    assert len(outbox) == 1


def test_failed_send_can_be_retried_at_once(client, with_email, outbox, monkeypatch):
    def broken(*_a):
        raise OSError("smtp down")
    monkeypatch.setattr("services.auth.send_email", broken)
    assert FORGOT_SENT in client.post("/admin/forgot", data={"email": EMAIL}).get_data(as_text=True)
    monkeypatch.setattr("services.auth.send_email", lambda to, subject, body: outbox.append((to, subject, body)))
    client.post("/admin/forgot", data={"email": EMAIL})
    assert len(outbox) == 1


def test_forgot_says_so_when_email_is_not_set_up(client, with_email):
    html = client.post("/admin/forgot", data={"email": EMAIL}).get_data(as_text=True)
    assert "Email sending is not set up" in html


# --- reset link ------------------------------------------------------------

def _request_link(client, outbox):
    client.post("/admin/forgot", data={"email": EMAIL})
    return _path(_reset_link(outbox))


def _reset(client, path, new=NEW_PASSWORD, confirm=None):
    return client.post(path, data={"new_password": new, "confirm_password": new if confirm is None else confirm})


def test_reset_link_sets_a_new_password(app, client, with_email, outbox):
    path = _request_link(client, outbox)
    assert client.get(path).status_code == 200
    resp = _reset(client, path)
    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]
    assert _login(app.test_client(), NEW_PASSWORD).status_code == 302
    assert _login(app.test_client(), PASSWORD, ip="198.51.100.9").status_code == 200


def test_reset_link_works_only_once(client, with_email, outbox):
    path = _request_link(client, outbox)
    _reset(client, path)
    assert "no longer valid" in client.get(path).get_data(as_text=True)
    assert _reset(client, path, new="yet-another-long-password").status_code == 400


def test_reset_link_expires_after_30_minutes(client, with_email, outbox, monkeypatch):
    real = TimestampSigner.get_timestamp
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: real(self) - 31 * 60)
    path = _request_link(client, outbox)
    monkeypatch.setattr(TimestampSigner, "get_timestamp", real)
    assert "no longer valid" in client.get(path).get_data(as_text=True)


def test_tampered_link_is_rejected(client, with_email, outbox):
    path = _request_link(client, outbox)
    assert "no longer valid" in client.get(path[:-3] + "abc").get_data(as_text=True)


def test_reset_rejects_short_and_mismatched_passwords(app, client, with_email, outbox):
    path = _request_link(client, outbox)
    assert "at least 12 characters" in _reset(client, path, new="short").get_data(as_text=True)
    assert "The two new passwords" in _reset(client, path, confirm=NEW_PASSWORD + "x").get_data(as_text=True)
    assert _login(app.test_client(), PASSWORD).status_code == 302  # unchanged


def test_reset_signs_out_other_sessions(app, as_admin, with_email, outbox):  # noqa: F811
    path = _request_link(app.test_client(), outbox)
    _reset(app.test_client(), path)
    resp = as_admin.get("/admin/")
    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]


def test_reset_clears_the_lockout_for_that_address(app, client, with_email, outbox):
    for _ in range(5):
        _login(client, "wrong")
    path = _request_link(client, outbox)
    client.post(path, data={"new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
                environ_base={"REMOTE_ADDR": "203.0.113.5"})
    assert _login(client, NEW_PASSWORD).status_code == 302


# --- recovery email in Settings --------------------------------------------

def _set_email(client, email, current=PASSWORD):
    return client.post("/admin/settings/email", data={"email": email, "current_password": current})


def test_recovery_email_needs_the_current_password(as_admin):  # noqa: F811
    resp = _set_email(as_admin, "new@example.test", current="not-it")
    assert resp.status_code == 400 and "current password is not right" in resp.get_data(as_text=True)
    assert db.session.scalar(db.select(Admin)).email is None


def test_recovery_email_rejects_a_bad_address(as_admin):  # noqa: F811
    resp = _set_email(as_admin, "not an email")
    assert resp.status_code == 400 and "valid email" in resp.get_data(as_text=True)


def test_recovery_email_is_saved_lower_case_and_shown(as_admin):  # noqa: F811
    assert _set_email(as_admin, " TTurf@Example.TEST ").status_code == 302
    db.session.expire_all()
    assert db.session.scalar(db.select(Admin)).email == "tturf@example.test"
    assert "tturf@example.test" in as_admin.get("/admin/settings").get_data(as_text=True)


def test_recovery_email_requires_login(client, admin_user):  # noqa: F811
    resp = _set_email(client, "x@example.test")
    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]
