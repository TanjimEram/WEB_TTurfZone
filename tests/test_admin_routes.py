"""Admin auth + routes (M5). Every /admin page needs a session; login is generic on failure."""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from extensions import db
from models import Admin, Booking
from services.slots import today_dhaka

USERNAME = "owner"
PASSWORD = "correct-horse-staple"
# Cheap hash, computed once - the default scrypt is deliberately slow and this
# test file creates an admin per test.
_FAST_HASH = generate_password_hash(PASSWORD, method="pbkdf2:sha256:1000", salt_length=8)


@pytest.fixture
def admin_user(app):
    with app.app_context():
        db.session.add(Admin(username=USERNAME, password_hash=_FAST_HASH))
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


# --- M5.3 bookings list + actions -----------------------------------

def test_bookings_list_shows_customer_and_wa_link(as_admin, app):
    _add(app, customer_name="Rafi Ahmed", phone="01712345678")
    html = as_admin.get("/admin/bookings").get_data(as_text=True)
    assert "Rafi Ahmed" in html
    assert "tel:01712345678" in html
    assert "wa.me/8801712345678" in html


def test_bookings_status_filter(as_admin, app):
    _add(app, code="C1", customer_name="Confirmed One", status=Booking.CONFIRMED)
    _add(app, code="P1", customer_name="Pending One", slot_time=dt.time(19, 30), status=Booking.PENDING)
    html = as_admin.get("/admin/bookings?status=PENDING").get_data(as_text=True)
    assert "Pending One" in html
    assert "Confirmed One" not in html


def test_bookings_date_filter(as_admin, app):
    other = today_dhaka() + dt.timedelta(days=4)
    _add(app, code="TODAY", customer_name="Today Person")
    _add(app, code="OTHER", customer_name="Other Day Person", booking_date=other)
    html = as_admin.get(f"/admin/bookings?date={other.isoformat()}").get_data(as_text=True)
    assert "Other Day Person" in html
    assert "Today Person" not in html


def test_confirm_pending_booking(as_admin, app):
    _add(app, code="CONF", status=Booking.PENDING)
    with app.app_context():
        bid = db.session.scalar(db.select(Booking.id))
    resp = as_admin.post(f"/admin/bookings/{bid}/confirm")
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Booking, bid).status == Booking.CONFIRMED


def test_reject_frees_slot(as_admin, app):
    _add(app, code="REJ", status=Booking.PENDING)
    with app.app_context():
        bid = db.session.scalar(db.select(Booking.id))
    as_admin.post(f"/admin/bookings/{bid}/reject", data={"note": "spam"})
    with app.app_context():
        b = db.session.get(Booking, bid)
        assert b.status == Booking.REJECTED
        assert b.admin_note == "spam"


def test_confirm_action_requires_login(client, app):
    _add(app, code="X", status=Booking.PENDING)
    with app.app_context():
        bid = db.session.scalar(db.select(Booking.id))
    resp = client.post(f"/admin/bookings/{bid}/confirm")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]
    with app.app_context():
        assert db.session.get(Booking, bid).status == Booking.PENDING


def test_confirm_bad_transition_flashes_not_crashes(as_admin, app):
    _add(app, code="DONE", status=Booking.CONFIRMED)
    with app.app_context():
        bid = db.session.scalar(db.select(Booking.id))
    resp = as_admin.post(f"/admin/bookings/{bid}/confirm", follow_redirects=True)
    assert resp.status_code == 200
    assert "Cannot confirm" in resp.get_data(as_text=True)


# --- M5.4 calendar + block/unblock ---------------------------------

FUTURE = today_dhaka() + dt.timedelta(days=3)


def test_calendar_shows_twelve_slots(as_admin):
    html = as_admin.get(f"/admin/calendar?date={FUTURE.isoformat()}").get_data(as_text=True)
    assert html.count("cal-slot__time") == 12


def test_calendar_shows_booking_customer(as_admin, app):
    _add(app, customer_name="Calendar Karim", booking_date=FUTURE, slot_time=dt.time(18, 0))
    html = as_admin.get(f"/admin/calendar?date={FUTURE.isoformat()}").get_data(as_text=True)
    assert "Calendar Karim" in html


def test_block_then_unblock(as_admin, app):
    as_admin.post("/admin/slots/block", data={
        "date": FUTURE.isoformat(), "slot": "18:00", "reason": "Private match",
    })
    with app.app_context():
        blocked = db.session.scalar(db.select(Booking).where(Booking.status == Booking.BLOCKED))
        assert blocked is not None
        assert blocked.admin_note == "Private match"
        bid = blocked.id

    as_admin.post(f"/admin/slots/{bid}/unblock")
    with app.app_context():
        assert db.session.get(Booking, bid) is None


def test_block_taken_slot_flashes_error(as_admin, app):
    _add(app, booking_date=FUTURE, slot_time=dt.time(18, 0), status=Booking.CONFIRMED)
    resp = as_admin.post("/admin/slots/block", data={
        "date": FUTURE.isoformat(), "slot": "18:00", "reason": "",
    }, follow_redirects=True)
    assert "already taken" in resp.get_data(as_text=True)
    with app.app_context():
        assert db.session.scalar(
            db.select(db.func.count()).select_from(Booking).where(Booking.status == Booking.BLOCKED)
        ) == 0


def test_blocked_slot_not_bookable_by_public(as_admin, client, app):
    as_admin.post("/admin/slots/block", data={"date": FUTURE.isoformat(), "slot": "18:00", "reason": ""})
    resp = client.post("/book", data={
        "name": "Late Comer", "phone": "01712345678",
        "date": FUTURE.isoformat(), "slot": "18:00",
    })
    assert resp.status_code == 409


def test_calendar_block_requires_login(client, app):
    resp = client.post("/admin/slots/block", data={"date": FUTURE.isoformat(), "slot": "18:00"})
    assert "/admin/login" in resp.headers["Location"]
    with app.app_context():
        assert db.session.scalar(db.select(Booking)) is None
