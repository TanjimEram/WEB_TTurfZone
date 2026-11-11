"""Public routes: homepage quick-book picker, /book page + form, /book/success (M4.2-M4.5, CR-9)."""
import datetime as dt
import itertools
import re

import pytest

from extensions import db
from models import Booking, TurfSettings
from services.slots import TZ, current_operating_day, today_dhaka
from tests.conftest import BKASH_NUMBER, CUSTOMER, open_booking, sign_in

SOON = today_dhaka() + dt.timedelta(days=5)
SIX_PM = dt.time(18, 0)


_TRX = (f"TRX{n:07d}" for n in itertools.count(1))


@pytest.fixture(autouse=True)
def _signed_in_and_open(app, client):
    """CR-9: booking needs a Google sign-in and the owner's bKash number in Settings."""
    sign_in(client)
    open_booking()


def _post_booking(client, name="Rafi Ahmed", phone="01712345678", date=None, slot="18:00", **extra):
    data = {
        "name": name,
        "phone": phone,
        "date": (date or SOON).isoformat() if hasattr(date or SOON, "isoformat") else (date or SOON),
        "slot": slot,
        "payer_number": "01812345678",
        "trx_id": next(_TRX),
        "no_refund": "1",
    }
    data.update(extra)
    return client.post("/book", data=data)


def _make_booking(app, name="Hidden Customer", phone="01711111111"):
    with app.app_context():
        db.session.add(Booking(
            booking_code="TZ-PUB001",
            customer_name=name,
            phone=phone,
            booking_date=dt.date(2099, 6, 1),
            slot_time=dt.time(18, 0),
            status=Booking.CONFIRMED,
        ))
        db.session.commit()


def test_book_page_renders(client):
    resp = client.get("/book")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "data-slotpicker" in html
    assert "js/booking.js" in html


def test_homepage_has_picker_and_script(client):
    html = client.get("/").get_data(as_text=True)
    assert "data-slotpicker" in html
    assert "js/booking.js" in html
    # progressive enhancement: a no-JS fallback is present
    assert "data-fallback" in html


def test_picker_has_one_chip_per_window_day(client):
    """Default booking_window_days is 14, so 14 date chips render."""
    html = client.get("/").get_data(as_text=True)
    assert html.count('class="datechip"') == 14


def _chip_dates(html):
    return re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"', html)


def _pressed_date(html):
    """The iso date of the chip button that has aria-pressed=true."""
    match = re.search(
        r'data-date="(\d{4}-\d{2}-\d{2})"\s+aria-pressed="true"', html
    )
    return match.group(1) if match else None


def test_book_preselects_valid_date(client):
    target = _chip_dates(client.get("/").get_data(as_text=True))[3]
    html = client.get(f"/book?date={target}").get_data(as_text=True)
    assert _pressed_date(html) == target
    assert html.count('aria-pressed="true"') == 1


def test_book_ignores_out_of_window_date(client):
    html = client.get("/book?date=2099-01-01").get_data(as_text=True)
    assert 'data-date="2099-01-01"' not in html
    # falls back to the first chip
    assert _pressed_date(html) == _chip_dates(html)[0]
    assert html.count('aria-pressed="true"') == 1


def test_date_chips_show_dates_not_today(client):
    html = client.get("/book").get_data(as_text=True)
    chips = re.findall(r'class="datechip"[^>]*>([^<]+)<', html)
    assert "Today" not in chips and "Tomorrow" not in chips
    assert chips[0] == current_operating_day().strftime("%a %d %b")


def test_book_page_preselects_operating_day_for_night_slot(client):
    day = current_operating_day() + dt.timedelta(days=2)
    html = client.get(f"/book?date={(day + dt.timedelta(days=1)).isoformat()}&slot=01:00").get_data(as_text=True)
    assert _pressed_date(html) == day.isoformat()
    assert 'data-preselect-slot="01:00"' in html


def test_booking_after_midnight_slot_uses_real_date(client, app, monkeypatch):
    monkeypatch.setattr("services.slots.now_dhaka", lambda: dt.datetime(2026, 11, 11, 12, 0, tzinfo=TZ))
    resp = _post_booking(client, date=dt.date(2026, 11, 12), slot="01:00")
    assert resp.status_code == 302
    with app.app_context():
        row = db.session.scalar(db.select(Booking))
        assert (row.booking_date, row.slot_time) == (dt.date(2026, 11, 12), dt.time(1, 0))


def test_book_requires_google_sign_in(app):
    fresh = app.test_client()
    for resp in (fresh.get("/book?date=2026-11-12&slot=01:00"), fresh.post("/book", data={})):
        assert resp.status_code == 302 and "/login?next=" in resp.headers["Location"]


def test_book_page_shows_payment_instructions_and_signed_in_email(client):
    html = client.get("/book").get_data(as_text=True)
    assert BKASH_NUMBER in html and "Payment" in html and "৳500" in html
    assert CUSTOMER["email"] in html
    assert 'value="Rafi Ahmed"' in html  # name prefilled from Google
    for field in ("payer_number", "trx_id", "no_refund"):
        assert f'name="{field}"' in html
    assert 'name="email"' not in html


def test_email_comes_from_google_session_not_form(client, app):
    assert _post_booking(client, email="someone.else@example.test").status_code == 302
    with app.app_context():
        assert db.session.execute(db.select(Booking)).scalar_one().customer_email == CUSTOMER["email"]


def test_no_refund_box_required(client, app):
    resp = _post_booking(client, no_refund="")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400 and "advance" in html and "refunded" in html
    with app.app_context():
        assert db.session.execute(db.select(Booking)).first() is None


def test_used_trx_id_is_refused_on_the_form(client, app):
    _post_booking(client, trx_id="8N7A6D5E4F")
    resp = _post_booking(client, slot="19:00", trx_id="8n7a6d5e4f")
    assert resp.status_code == 400
    assert "already been used" in resp.get_data(as_text=True)


def test_booking_closed_without_bkash_number(client, app):
    open_booking(bkash_number="")
    html = client.get("/book").get_data(as_text=True)
    assert "open yet" in html and 'name="trx_id"' not in html
    assert _post_booking(client).status_code == 400
    with app.app_context():
        assert db.session.execute(db.select(Booking)).first() is None


def test_book_passes_slot_through_to_js(client):
    html = client.get("/book?date=2099-01-01&slot=18:00").get_data(as_text=True)
    assert 'data-preselect-slot="18:00"' in html


def test_no_customer_data_on_book_page(client, app):
    _make_booking(app)
    html = client.get("/book").get_data(as_text=True)
    assert "Hidden Customer" not in html
    assert "01711111111" not in html


# --- POST /book + /book/success (M4.3-M4.5) --------------------------

def test_booking_happy_path(client, app):
    resp = _post_booking(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/book/success")

    page = client.get("/book/success")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Payment being checked" in html
    assert "Rafi Ahmed" in html
    assert "player@gmail.com" in html  # where the confirmation will go

    with app.app_context():
        booking = db.session.execute(db.select(Booking)).scalar_one()
        assert booking.status == Booking.PENDING
        assert booking.phone == "01712345678"
        assert booking.customer_email == "player@gmail.com"
        assert booking.booking_code in html and booking.trx_id in html


def test_booking_invalid_phone_rerenders_form(client, app):
    resp = _post_booking(client, phone="123")
    assert resp.status_code == 400
    assert "Enter a valid Bangladeshi mobile number" in resp.get_data(as_text=True)
    with app.app_context():
        assert db.session.execute(db.select(Booking)).first() is None


def test_booking_blank_name_rerenders_form(client, app):
    resp = _post_booking(client, name="   ")
    assert resp.status_code == 400
    assert "Enter your name" in resp.get_data(as_text=True)


def test_booking_taken_slot_shows_friendly_error(client, app):
    _post_booking(client)  # takes 18:00
    resp = _post_booking(client, name="Someone Else", phone="01812345678")
    assert resp.status_code == 409
    assert "just taken" in resp.get_data(as_text=True)


def test_booking_past_slot_rejected(client, app):
    yesterday = today_dhaka() - dt.timedelta(days=1)
    resp = _post_booking(client, date=yesterday)
    assert resp.status_code == 400
    with app.app_context():
        assert db.session.execute(db.select(Booking)).first() is None


def test_booking_missing_slot_rejected(client, app):
    resp = _post_booking(client, date="", slot="")
    assert resp.status_code == 400
    assert "Pick a date and time" in resp.get_data(as_text=True)


def test_success_without_session_redirects_home(client):
    resp = client.get("/book/success")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


def test_success_is_one_time_only(client, app):
    _post_booking(client)
    assert client.get("/book/success").status_code == 200
    # refresh: session already consumed
    again = client.get("/book/success")
    assert again.status_code == 302
    assert again.headers["Location"].endswith("/")


def test_success_whatsapp_link_when_number_set(client, app):
    open_booking(whatsapp="8801712345678")
    _post_booking(client)
    html = client.get("/book/success").get_data(as_text=True)
    assert "https://wa.me/8801712345678?text=" in html
    assert "Chat on WhatsApp" in html


def test_success_no_whatsapp_link_when_unset(client, app):
    _post_booking(client)
    html = client.get("/book/success").get_data(as_text=True)
    assert "wa.me" not in html
    assert "C-06" in html  # the TODO(owner) note instead


def _dead_hash_links(html):
    """href="#x" whose id="x" is not on the same page (a link that does nothing)."""
    targets = set(re.findall(r'href="#([\w-]+)"', html))
    return sorted(t for t in targets if f'id="{t}"' not in html)


def test_no_dead_section_links_on_any_public_page(client, app):
    """Regression: the shared nav/footer/sticky bar used to link #about, #book etc.
    which only exist on the homepage, so they did nothing on /book."""
    assert _dead_hash_links(client.get("/").get_data(as_text=True)) == []
    assert _dead_hash_links(client.get("/book").get_data(as_text=True)) == []
    _post_booking(client)
    assert _dead_hash_links(client.get("/book/success").get_data(as_text=True)) == []


def test_book_now_goes_to_booking_page_off_homepage(client):
    html = client.get("/book").get_data(as_text=True)
    assert 'href="/book">Book now' in html
    assert 'href="/#about"' in html
