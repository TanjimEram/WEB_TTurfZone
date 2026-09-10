"""Homepage (M3.2). Renders entirely from turf_settings; leaks no customer data."""
import datetime as dt

import pytest

from extensions import db
from models import Booking, TurfSettings

SECTION_IDS = ["book", "about", "facilities", "pricing", "gallery", "location", "reviews", "facebook"]


@pytest.fixture
def home(client):
    return client.get("/")


def test_homepage_ok(home):
    assert home.status_code == 200


def test_every_section_present(home):
    html = home.get_data(as_text=True)
    for section_id in SECTION_IDS:
        assert f'id="{section_id}"' in html, f"missing section #{section_id}"


def test_hero_and_footer_present(home):
    html = home.get_data(as_text=True)
    assert "hero__title" in html
    assert "site-footer" in html
    # the 12 slot labels show in the quick-book placeholder grid
    assert "06:00 AM" in html and "10:30 PM" in html


def test_sticky_mobile_bar_present(home):
    """Brief §11: persistent mobile WHATSAPP + BOOK NOW actions."""
    html = home.get_data(as_text=True)
    assert 'class="sticky-actions"' in html
    bar = html.split('class="sticky-actions"', 1)[1].split("</div>", 1)[0]
    assert "WhatsApp" in bar
    assert "Book now" in bar


def test_nav_has_mobile_menu_and_script(home):
    html = home.get_data(as_text=True)
    assert "nav__toggle" in html
    assert 'id="nav-menu"' in html
    assert "js/main.js" in html


def test_missing_owner_content_shows_todo_notes(home):
    """With no seeded settings row, every gap is a visible TODO(owner) marker."""
    html = home.get_data(as_text=True)
    assert "TODO(owner)" in html
    for code in ["C-17", "C-16", "C-02", "C-07", "C-13"]:
        assert code in html, f"no TODO note references {code}"


def test_homepage_uses_seeded_settings(client, app):
    with app.app_context():
        db.session.add(TurfSettings(turf_name="TTURFZONE", about_text="A real six-a-side turf in Jashore."))
        db.session.commit()
    html = client.get("/").get_data(as_text=True)
    assert "A real six-a-side turf in Jashore." in html


def test_no_customer_data_on_homepage(client, app):
    """A booking's name and phone must never appear on the public homepage."""
    with app.app_context():
        db.session.add(Booking(
            booking_code="TZ-TEST01",
            customer_name="R;t Nahid Chowdhury",
            phone="01712345678",
            booking_date=dt.date.today() + dt.timedelta(days=1),
            slot_time=dt.time(18, 0),
            status=Booking.CONFIRMED,
        ))
        db.session.commit()
    html = client.get("/").get_data(as_text=True)
    assert "Nahid Chowdhury" not in html
    assert "01712345678" not in html


def test_availability_api_has_no_customer_data(client, app):
    with app.app_context():
        db.session.add(Booking(
            booking_code="TZ-TEST02",
            customer_name="Private Person",
            phone="01898765432",
            booking_date=dt.date(2099, 1, 1),
            slot_time=dt.time(18, 0),
            status=Booking.CONFIRMED,
        ))
        db.session.commit()
    body = client.get("/api/availability?date=2099-01-01").get_data(as_text=True)
    assert "Private Person" not in body
    assert "01898765432" not in body
