"""Public routes: homepage quick-book picker, /book page + form, /book/success (M4.2-M4.5)."""
import datetime as dt
import re

from extensions import db
from models import Booking, TurfSettings
from services.slots import today_dhaka

SOON = today_dhaka() + dt.timedelta(days=5)
SIX_PM = dt.time(18, 0)


def _post_booking(client, name="Rafi Ahmed", phone="01712345678", date=None, slot="18:00"):
    return client.post("/book", data={
        "name": name,
        "phone": phone,
        "date": (date or SOON).isoformat() if hasattr(date or SOON, "isoformat") else (date or SOON),
        "slot": slot,
    })


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
    assert "Booking request received" in html
    assert "Pending" in html
    assert "Rafi Ahmed" in html

    with app.app_context():
        booking = db.session.execute(db.select(Booking)).scalar_one()
        assert booking.status == Booking.PENDING
        assert booking.phone == "01712345678"
        assert booking.booking_code in html


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
    resp = client.post("/book", data={"name": "Rafi", "phone": "01712345678", "date": "", "slot": ""})
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
    with app.app_context():
        db.session.add(TurfSettings(turf_name="TTURFZONE", whatsapp="8801712345678"))
        db.session.commit()
    _post_booking(client)
    html = client.get("/book/success").get_data(as_text=True)
    assert "https://wa.me/8801712345678?text=" in html
    assert "Chat on WhatsApp" in html


def test_success_no_whatsapp_link_when_unset(client, app):
    _post_booking(client)
    html = client.get("/book/success").get_data(as_text=True)
    assert "wa.me" not in html
    assert "C-06" in html  # the TODO(owner) note instead
