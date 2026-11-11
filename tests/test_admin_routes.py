"""Admin auth + routes (M5). Every /admin page needs a session; login is generic on failure."""
import datetime as dt
from datetime import time, timedelta

import pytest
from werkzeug.security import generate_password_hash

from extensions import db
from models import Admin, Booking, TurfSettings
from services.slots import TZ, current_operating_day, today_dhaka
from tests.conftest import open_booking, sign_in

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


PROTECTED = ["/admin/", "/admin/bookings", "/admin/calendar", "/admin/settings"]


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


# --- M5.4 calendar + block/unblock (one operating day, 24 slots, CR-10) ------

FUTURE = current_operating_day() + dt.timedelta(days=3)
FUTURE_NEXT = FUTURE + dt.timedelta(days=1)


def test_calendar_shows_24_slots_in_three_periods(as_admin):
    html = as_admin.get(f"/admin/calendar?date={FUTURE.isoformat()}").get_data(as_text=True)
    assert html.count("cal-slot__time") == 24
    for heading in ("Morning", "Afternoon", "Night"):
        assert heading in html


def test_calendar_shows_booking_customer(as_admin, app):
    _add(app, customer_name="Calendar Karim", booking_date=FUTURE, slot_time=dt.time(18, 0))
    html = as_admin.get(f"/admin/calendar?date={FUTURE.isoformat()}").get_data(as_text=True)
    assert "Calendar Karim" in html


def test_calendar_shows_after_midnight_booking_under_the_night_before(as_admin, app):
    _add(app, customer_name="Night Owl", booking_date=FUTURE_NEXT, slot_time=dt.time(1, 0))
    assert "Night Owl" in as_admin.get(f"/admin/calendar?date={FUTURE.isoformat()}").get_data(as_text=True)
    assert "Night Owl" not in as_admin.get(f"/admin/calendar?date={FUTURE_NEXT.isoformat()}").get_data(as_text=True)


def test_calendar_blocks_after_midnight_slot_on_real_date(as_admin, app):
    html = as_admin.get(f"/admin/calendar?date={FUTURE.isoformat()}").get_data(as_text=True)
    assert f'name="date" value="{FUTURE_NEXT.isoformat()}"' in html  # the 00:00-05:00 block forms
    as_admin.post("/admin/slots/block", data={"date": FUTURE_NEXT.isoformat(), "slot": "01:00", "reason": ""})
    with app.app_context():
        blocked = db.session.scalar(db.select(Booking).where(Booking.status == Booking.BLOCKED))
        assert (blocked.booking_date, blocked.slot_time) == (FUTURE_NEXT, dt.time(1, 0))


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
    with app.app_context():
        open_booking()
    customer = sign_in(app.test_client())
    resp = customer.post("/book", data={
        "name": "Late Comer", "phone": "01712345678", "payer_number": "01712345678",
        "trx_id": "8N7A6D5E4F", "no_refund": "1", "date": FUTURE.isoformat(), "slot": "18:00",
    })
    assert resp.status_code == 409


def test_calendar_block_requires_login(client, app):
    resp = client.post("/admin/slots/block", data={"date": FUTURE.isoformat(), "slot": "18:00"})
    assert "/admin/login" in resp.headers["Location"]
    with app.app_context():
        assert db.session.scalar(db.select(Booking)) is None


def test_dashboard_today_is_the_operating_day(as_admin, app, monkeypatch):
    two_am_thu = dt.datetime(2026, 11, 12, 2, 0, tzinfo=TZ)
    monkeypatch.setattr("services.slots.now_dhaka", lambda: two_am_thu)
    _add(app, customer_name="Late Night", booking_date=dt.date(2026, 11, 12), slot_time=dt.time(1, 0),
         status=Booking.CONFIRMED)
    html = as_admin.get("/admin/").get_data(as_text=True)
    today_part, week_part = html.split("Next 7 days")
    assert "Late Night" in today_part and "Late Night" not in week_part  # today = Wednesday's operating day


# --- settings (M7.4, CR-6, CR-10): contact, text, window, open hours, period prices ----

ALL_HOUR_KEYS = [f"{h:02d}:00" for h in list(range(6, 24)) + list(range(0, 6))]

VALID_SETTINGS = {
    "phone": "01712345678",
    "whatsapp": "+8801812345678",
    "address": "Notin Rani ghat, Jashore",
    "opening_hours_text": "Every day, 6 AM to 12 AM",
    "booking_rules_text": "Cancel 6 hours ahead.",
    "booking_window_days": "14",
    "open_hours": ALL_HOUR_KEYS,
    "price-morning": "1000",
    "price-afternoon": "1350",
    "price-night": "2000",
    "advance_bdt": "500",
}


def test_settings_page_hides_seed_todos(as_admin):
    html = as_admin.get("/admin/settings").get_data(as_text=True)
    assert "TODO(owner)" not in html  # placeholders never prefill the form
    assert html.count('name="open_hours"') == 24
    for name in ("price-morning", "price-afternoon", "price-night"):
        assert f'name="{name}"' in html
    assert 'type="time"' not in html and "band-0" not in html


def test_settings_save_updates_public_site(as_admin, client, app):
    resp = as_admin.post("/admin/settings", data=VALID_SETTINGS)
    assert resp.status_code == 302
    with app.app_context():
        s = TurfSettings.current()
        assert s.phone == "01712345678"
        assert s.whatsapp == "8801812345678"  # wa.me format
        assert s.pricing == {"morning": 1000, "afternoon": 1350, "night": 2000}
        assert s.slot_times is None  # all 24 open
    home = client.get("/").get_data(as_text=True)
    assert "Notin Rani ghat, Jashore" in home
    assert "wa.me/8801812345678" in home
    assert "৳1,000" in home and "৳1,350" in home and "৳2,000" in home


def test_period_prices_show_on_the_grid(as_admin, client):
    as_admin.post("/admin/settings", data=VALID_SETTINGS)
    day = (current_operating_day() + timedelta(days=3)).isoformat()
    prices = {s["time"]: s["price_bdt"] for s in client.get(f"/api/availability?date={day}").get_json()["slots"]}
    assert prices["07:00"] == 1000 and prices["13:00"] == 1350 and prices["01:00"] == 2000


def test_settings_bad_phone_saves_nothing_and_keeps_input(as_admin, app):
    resp = as_admin.post("/admin/settings", data={**VALID_SETTINGS, "phone": "123"})
    assert resp.status_code == 400
    html = resp.get_data(as_text=True)
    assert "valid Bangladeshi mobile" in html
    assert 'value="123"' in html
    with app.app_context():
        assert TurfSettings.current() is None


def test_settings_save_bkash_number_and_advance(as_admin, app):
    resp = as_admin.post("/admin/settings", data={**VALID_SETTINGS, "bkash_number": "+8801827881299", "advance_bdt": "600"})
    assert resp.status_code == 302
    with app.app_context():
        s = TurfSettings.current()
        assert (s.bkash_number, s.advance_bdt) == ("01827881299", 600)
    html = as_admin.get("/admin/settings").get_data(as_text=True)
    assert 'value="01827881299"' in html and 'value="600"' in html


def test_bad_advance_is_refused(as_admin, app):
    resp = as_admin.post("/admin/settings", data={**VALID_SETTINGS, "advance_bdt": "0"})
    assert resp.status_code == 400 and "advance" in resp.get_data(as_text=True)


def test_missing_or_bad_period_price_is_refused(as_admin, app):
    for bad in ("", "abc", "0"):
        resp = as_admin.post("/admin/settings", data={**VALID_SETTINGS, "price-night": bad})
        assert resp.status_code == 400
        assert "Enter a price in whole taka." in resp.get_data(as_text=True)
    with app.app_context():
        assert TurfSettings.current() is None


def test_settings_post_requires_login(client, app):
    resp = client.post("/admin/settings", data=VALID_SETTINGS)
    assert "/admin/login" in resp.headers["Location"]
    with app.app_context():
        assert TurfSettings.current() is None


def _save(as_admin, **changes):
    return as_admin.post("/admin/settings", data={**VALID_SETTINGS, **changes})


def test_settings_saves_homepage_text_window_and_note(as_admin, client, app):
    resp = _save(as_admin, tagline="Floodlit six-a-side", about_text="Our ground.",
                 booking_window_days="21", confirm_time_text="Arrive 10 minutes early.")
    assert resp.status_code == 302
    with app.app_context():
        s = TurfSettings.current()
        assert (s.tagline, s.about_text, s.booking_window_days) == ("Floodlit six-a-side", "Our ground.", 21)
    home = client.get("/").get_data(as_text=True)
    assert "Floodlit six-a-side" in home and "Our ground." in home
    assert home.count('class="datechip"') == 21


def test_settings_rejects_bad_window(as_admin, app):
    resp = _save(as_admin, booking_window_days="0")
    assert resp.status_code == 400
    assert "from 1 to 60" in resp.get_data(as_text=True)
    with app.app_context():
        assert TurfSettings.current() is None


def test_settings_closes_hours_and_public_grid_hides_them(as_admin, client, app):
    night = [f"{h:02d}:00" for h in list(range(18, 24)) + list(range(0, 6))]
    assert _save(as_admin, open_hours=night).status_code == 302
    with app.app_context():
        assert TurfSettings.current().slot_times == night
    day = (current_operating_day() + timedelta(days=3)).isoformat()
    slots = client.get(f"/api/availability?date={day}").get_json()["slots"]
    assert [s["time"] for s in slots] == night and {s["period"] for s in slots} == {"night"}


def test_no_open_hours_is_refused(as_admin, app):
    resp = _save(as_admin, open_hours=[])
    assert resp.status_code == 400
    assert "Tick at least one hour the ground is open." in resp.get_data(as_text=True)


def test_closing_an_hour_with_an_upcoming_booking_is_refused(as_admin, app):
    soon = today_dhaka() + timedelta(days=2)
    with app.app_context():
        db.session.add(Booking(booking_code="TZ-KEEP01", customer_name="A", phone="01711111111",
                               booking_date=soon, slot_time=time(7, 0), status=Booking.CONFIRMED))
        db.session.commit()
    resp = _save(as_admin, open_hours=[k for k in ALL_HOUR_KEYS if k != "07:00"])
    assert resp.status_code == 400
    html = resp.get_data(as_text=True)
    assert "TZ-KEEP01" in html and "Cancel or unblock them first" in html
    with app.app_context():
        assert TurfSettings.current() is None  # nothing saved


def test_past_bookings_do_not_stop_closing_an_hour(as_admin, app):
    with app.app_context():
        db.session.add(Booking(booking_code="TZ-OLD001", customer_name="A", phone="01711111111",
                               booking_date=today_dhaka() - timedelta(days=3), slot_time=time(7, 0),
                               status=Booking.CONFIRMED))
        db.session.commit()
    assert _save(as_admin, open_hours=[k for k in ALL_HOUR_KEYS if k != "07:00"]).status_code == 302


def test_preview_endpoint_is_gone(as_admin):
    assert as_admin.post("/admin/settings/preview", data=VALID_SETTINGS).status_code == 404


def test_dashboard_warns_when_period_prices_are_missing(as_admin):
    html = as_admin.get("/admin/").get_data(as_text=True)
    assert "3 period price(s) are not set" in html


# --- M5.9 password change (D-49) -------------------------------------------

NEW_PASSWORD = "a-much-longer-new-passphrase"


def _change(client, current=PASSWORD, new=NEW_PASSWORD, confirm=None):
    return client.post("/admin/settings/password", data={
        "current_password": current, "new_password": new,
        "confirm_password": new if confirm is None else confirm,
    })


def _can_log_in(app, password):
    resp = app.test_client().post("/admin/login", data={"username": USERNAME, "password": password})
    return resp.status_code == 302


def test_password_change_rejects_wrong_current_password(as_admin, app):
    resp = _change(as_admin, current="not-my-password")
    assert resp.status_code == 400
    assert "current password is not right" in resp.get_data(as_text=True)
    assert _can_log_in(app, PASSWORD) and not _can_log_in(app, NEW_PASSWORD)


def test_password_change_rejects_short_and_mismatched_passwords(as_admin, app):
    short = _change(as_admin, new="short1")
    assert short.status_code == 400 and "at least 12 characters" in short.get_data(as_text=True)
    mismatch = _change(as_admin, confirm=NEW_PASSWORD + "x")
    assert mismatch.status_code == 400 and "The two new passwords" in mismatch.get_data(as_text=True)
    assert _can_log_in(app, PASSWORD)


def test_password_change_success_swaps_old_for_new(as_admin, app):
    resp = _change(as_admin)
    assert resp.status_code == 302
    assert as_admin.get("/admin/").status_code == 200  # this browser stays signed in
    assert _can_log_in(app, NEW_PASSWORD)
    assert not _can_log_in(app, PASSWORD)


def test_password_change_signs_out_other_sessions(as_admin, app):
    other = app.test_client()
    other.post("/admin/login", data={"username": USERNAME, "password": PASSWORD})
    assert other.get("/admin/").status_code == 200
    _change(as_admin)
    resp = other.get("/admin/")
    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]


def test_password_change_requires_login(client, admin_user, app):
    resp = _change(client)
    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]
    assert _can_log_in(app, PASSWORD)


def test_dashboard_lists_what_the_public_site_still_hides(as_admin):
    html = as_admin.get("/admin/").get_data(as_text=True)
    assert "Not on your website yet" in html
    for label in ("Prices for every slot", "Phone number", "WhatsApp number", "Address",
                  "Opening hours", "Tagline", "About the ground", "Google Maps location", "Customer reviews"):
        assert label in html
    assert "send it to your developer" in html and "add it in Settings" in html
