"""Admin auth + routes (M5). Every /admin page needs a session; login is generic on failure."""
import pytest

from extensions import db
from models import Admin

USERNAME = "owner"
PASSWORD = "correct-horse-staple"


@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = Admin(username=USERNAME)
        admin.set_password(PASSWORD)
        db.session.add(admin)
        db.session.commit()
    return USERNAME


@pytest.fixture
def as_admin(client, admin_user):
    resp = client.post("/admin/login", data={"username": USERNAME, "password": PASSWORD})
    assert resp.status_code == 302
    return client


PROTECTED = ["/admin/", "/admin/bookings", "/admin/calendar"]


@pytest.mark.parametrize("path", PROTECTED)
def test_protected_pages_redirect_to_login_when_logged_out(client, path):
    resp = client.get(path)
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


@pytest.mark.parametrize("path", PROTECTED)
def test_protected_pages_open_when_logged_in(as_admin, path):
    assert as_admin.get(path).status_code == 200


def test_login_page_renders(client):
    assert client.get("/admin/login").status_code == 200


def test_wrong_password_is_generic(client, admin_user):
    resp = client.post("/admin/login", data={"username": USERNAME, "password": "nope"})
    assert resp.status_code == 200
    assert "Invalid username or password." in resp.get_data(as_text=True)


def test_unknown_user_is_generic(client):
    resp = client.post("/admin/login", data={"username": "ghost", "password": "x"})
    assert "Invalid username or password." in resp.get_data(as_text=True)


def test_login_redirects_to_dashboard(as_admin):
    resp = as_admin.post("/admin/login", data={"username": USERNAME, "password": PASSWORD})
    # already logged in -> straight to dashboard
    assert resp.headers["Location"].endswith("/admin/")


def test_login_honours_safe_next(client, admin_user):
    resp = client.post(
        "/admin/login?next=/admin/bookings",
        data={"username": USERNAME, "password": PASSWORD},
    )
    assert resp.headers["Location"].endswith("/admin/bookings")


def test_login_ignores_offsite_next(client, admin_user):
    resp = client.post(
        "/admin/login?next=https://evil.example/",
        data={"username": USERNAME, "password": PASSWORD},
    )
    assert resp.headers["Location"].endswith("/admin/")


def test_logout_clears_session(as_admin):
    assert as_admin.post("/admin/logout").status_code == 302
    assert as_admin.get("/admin/").status_code == 302  # back to needing login


def test_logout_requires_login(client):
    assert client.post("/admin/logout").status_code == 302


def test_admin_pages_are_noindex(as_admin):
    assert 'content="noindex' in as_admin.get("/admin/").get_data(as_text=True)
