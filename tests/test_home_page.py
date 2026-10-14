"""Homepage (M3.2). Renders entirely from turf_settings; leaks no customer data."""
import datetime as dt
import json
from pathlib import Path
import re

import pytest

from extensions import db
from models import Booking, TurfSettings

SECTION_IDS = ["book", "about", "pricing", "gallery", "location", "reviews", "facebook"]


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


def test_gallery_lightbox_present(home):
    """M7.2: every gallery photo is a lightbox trigger, plus the overlay + scripts."""
    html = home.get_data(as_text=True)
    assert html.count("data-lightbox-item") == 6
    assert 'data-lightbox-overlay' in html
    assert 'role="dialog"' in html
    assert "js/gallery.js" in html
    assert "js/reveal.js" in html


def test_missing_owner_content_shows_todo_notes(home):
    """With no seeded settings row, every gap is a visible TODO(owner) marker."""
    html = home.get_data(as_text=True)
    assert "TODO(owner)" in html
    for code in ["C-17", "C-02", "C-07"]:  # C-13 photos arrived in M7.1; C-16 dropped by CR-5
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


# --- M7.3: SEO / sharing tags -------------------------------------------

def test_favicon_and_og_tags_present(home):
    html = home.get_data(as_text=True)
    assert 'rel="icon"' in html
    assert 'rel="canonical"' in html
    assert 'property="og:title"' in html
    assert 'property="og:description"' in html
    assert 'name="twitter:card"' in html


def test_json_ld_present_with_only_confirmed_fields(home):
    """Unseeded settings are all TODO(owner) placeholders - JSON-LD must omit them, never invent."""
    html = home.get_data(as_text=True)
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert match, "no JSON-LD script tag on the homepage"
    data = json.loads(match.group(1))
    assert data["@type"] == "LocalBusiness"
    assert data["name"] == "TTURFZONE"
    assert "url" in data
    for missing in ("description", "telephone", "address"):
        assert missing not in data, f"{missing} should be omitted while still a TODO placeholder"


def test_json_ld_includes_confirmed_fields(client, app):
    with app.app_context():
        db.session.add(TurfSettings(
            turf_name="TTURFZONE",
            about_text="A real six-a-side turf in Jashore.",
            phone="01712345678",
            address="123 Real Street, Jashore",
        ))
        db.session.commit()
    html = client.get("/").get_data(as_text=True)
    data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
    assert data["description"] == "A real six-a-side turf in Jashore."
    assert data["telephone"] == "01712345678"
    assert data["address"] == "123 Real Street, Jashore"


def test_pricing_section_lists_resolved_bands(client, app):
    """M4.7: the price list is built from the same resolution as the slot grid."""
    evening = ["16:30", "18:00", "19:30", "21:00", "22:30"]
    with app.app_context():
        db.session.add(TurfSettings(turf_name="TTURFZONE", pricing=[
            {"label": "Daytime", "slots": ["06:00", "07:30", "09:00", "10:30", "12:00", "13:30", "15:00"],
             "days": "all", "price_bdt": 4000},
            {"label": "Evening", "slots": evening, "days": "all", "price_bdt": 4500},
            {"label": "Weekend evening", "slots": evening, "days": "weekend", "price_bdt": 5000},
        ]))
        db.session.commit()
    section = client.get("/").get_data(as_text=True).split('id="pricing"')[1].split("</section>")[0]
    assert "Sunday to Thursday" in section and "Friday and Saturday" in section
    assert "06:00 AM – 04:30 PM" in section and "৳4,000" in section
    assert "৳4,500" in section and "৳5,000" in section
    assert "TODO(owner)" not in section


def test_hidden_attribute_beats_component_display(client):
    """Regression: .lightbox is display:flex, so without a global [hidden] rule the
    closed lightbox overlay covered the whole homepage on every load (M7.2 bug)."""
    css = client.get("/static/css/main.css").get_data(as_text=True)
    assert "[hidden] { display: none !important; }" in css


# --- M7.1: real photos, logo, share image --------------------------------

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_every_photo_exists_in_every_width_as_4x3_without_metadata():
    """build_images.py output matches routes/public.py PHOTOS; width/height attrs assume 4:3;
    no EXIF means no phone GPS/device data reaches the public site."""
    from PIL import Image

    from routes.public import PHOTO_WIDTHS, PHOTOS
    for p in PHOTOS:
        for w in PHOTO_WIDTHS:
            path = STATIC / "images" / "photos" / f"{p['name']}-{w}.webp"
            assert path.exists(), f"missing {path.name}: run scripts/build_images.py"
            with Image.open(path) as im:
                assert im.size == (w, w * 3 // 4), path.name
                assert not im.getexif(), f"{path.name} still carries EXIF"


def test_homepage_shows_real_photos_with_alt_text(home):
    html = home.get_data(as_text=True)
    assert "Owner photo:" not in html  # no photo placeholders left
    imgs = re.findall(r"<img\s[^>]*>", html)
    photos = [i for i in imgs if "/images/photos/" in i]
    assert len(photos) == 1 + 2 + 6  # hero, about, gallery
    for tag in photos:
        alt = re.search(r'alt="([^"]*)"', tag).group(1)
        assert alt.strip(), f"photo without alt text: {tag}"
        assert "srcset=" in tag and 'width="1280"' in tag and 'height="960"' in tag
    hero, rest = photos[0], photos[1:]
    assert 'loading="eager"' in hero and 'fetchpriority="high"' in hero
    assert all('loading="lazy"' in tag for tag in rest)


def test_logo_icons_and_share_image(home):
    html = home.get_data(as_text=True)
    assert "logo-emblem-96.webp" in html
    og = re.search(r'property="og:image" content="([^"]+)"', html).group(1)
    assert og.startswith("http") and og.endswith("/static/images/og-image.jpg")
    assert 'name="twitter:card" content="summary_large_image"' in html
    for rel in ("images/og-image.jpg", "images/logo-emblem-96.webp", "icons/favicon-32.png", "icons/apple-touch-icon.png"):
        assert (STATIC / rel).exists(), rel


def test_no_facilities_section_or_link(home):
    """CR-5: the Facilities section was removed (column kept, unused)."""
    html = home.get_data(as_text=True)
    assert 'id="facilities"' not in html
    assert "#facilities" not in html
    assert "Facilities" not in html

