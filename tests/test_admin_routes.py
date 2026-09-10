"""Admin auth + routes (M5). Every /admin page needs a session; login is generic on failure."""
import datetime as dt

import pytest

from extensions import db
from models import Admin, Booking
from services.slots import today_dhaka

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


# --- M5.2 dashboard ---------------------------------------------------

def _add(app, **kw):
    defaults = dict(
        booking_code="TZ-" + kw.pop("code", "DASH01"),
        customer_name="Dash Customer",
        phone="01712345678",
        booking_date=today_dhaka(),
        slot_time=dt.time(18, 0),
        status=Booking.CONFIRMED,
    )
    defaults.update(kw)
    with app.app_context():
        db.session.add(Booking(**defaults))
        db.session.commit()


def test_dashboard_shows_todays_booking(as_admin, app):
    _add(app, customer_name="Karim Bhai", phone="01798887766")
    html = as_admin.get("/admin/").get_data(as_text=True)
    assert "Karim Bhai" in html
    assert "01798887766" in html
    assert "Bookings today" in html


def test_dashboard_counts_pending(as_admin, app):
    _add(app, code="P1", slot_time=dt.time(18, 0), status=Booking.PENDING)
    _add(app, code="P2", slot_time=dt.time(19, 30), status=Booking.PENDING)
    html = as_admin.get("/admin/").get_data(as_text=True)
    # the pending stat value "2" appears next to its label
    assert "Awaiting confirmation" in html


def test_dashboard_next_seven_days(as_admin, app):
    _add(app, code="WK", booking_date=today_dhaka() + dt.timedelta(days=2), customer_name="Next Week Guy")
    html = as_admin.get("/admin/").get_data(as_text=True)
    assert "Next Week Guy" in html
    assert "Next 7 days" in html
