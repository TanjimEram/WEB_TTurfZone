"""Public routes: homepage quick-book picker and the /book page (M4.2).

The details form and POST /book are M4.3 — not covered here yet.
"""
import datetime as dt
import re

from extensions import db
from models import Booking


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
