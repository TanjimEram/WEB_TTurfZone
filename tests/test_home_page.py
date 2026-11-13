"""Homepage (M3.2). Renders entirely from turf_settings; leaks no customer data."""
import datetime as dt
import json
from pathlib import Path
import re

import pytest

from extensions import db
from models import Booking, TurfSettings
from tests.conftest import open_booking

SECTION_IDS = ["book", "pricing", "about", "gallery", "why", "faq", "rules", "contact", "location", "reviews", "facebook"]


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
    assert "hero__name" in html
    assert "site-footer" in html
    # the 24 hourly slot labels show in the no-JS placeholder grid
    assert "06:00 AM" in html and "11:00 PM" in html and "05:00 AM" in html


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
    assert html.count("data-lightbox-item") == 5  # About Our Turf: one tall photo + 2x2 (CR-11)
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


def test_pricing_section_shows_one_card_per_period(client, app):
    """D-53: one price per period, the same every day, from the same function as the slot grid."""
    with app.app_context():
        db.session.add(TurfSettings(turf_name="TTURFZONE", pricing={"morning": 1000, "afternoon": 1350, "night": 2000}))
        db.session.commit()
    section = client.get("/").get_data(as_text=True).split('id="pricing"')[1].split("</section>")[0]
    for text in ("Morning", "6AM–12PM", "১,০০০৳", "Afternoon", "১,৩৫০৳", "Night", "6PM–6AM", "২,০০০৳"):
        assert text in section
    assert "TODO(owner)" not in section


def test_home_says_open_24_hours_when_all_hours_open(client):
    html = client.get("/").get_data(as_text=True)
    assert "Open 24 hours" in html and "90-minute" not in html


def test_home_span_follows_open_hours(client, app):
    with app.app_context():
        db.session.add(TurfSettings(turf_name="T", slot_times=["18:00", "19:00", "20:00", "21:00", "22:00", "23:00"]))
        db.session.commit()
    assert "06:00 PM to 12:00 AM" in client.get("/").get_data(as_text=True)


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
    assert len(photos) == 3 + 5 + 1  # one per part of the day, About our turf grid, Find the ground (CR-12)
    for tag in photos:
        alt = re.search(r'alt="([^"]*)"', tag).group(1)
        assert alt.strip(), f"photo without alt text: {tag}"
        assert "srcset=" in tag and 'width="1280"' in tag and 'height="960"' in tag
        assert 'loading="lazy"' in tag  # only the hero (its own sharpened files) loads eagerly


def test_hero_is_the_real_night_photo_sharpened_for_wide_screens(home):
    """CR-12: the hero is the owner's floodlights photo (the CR-7 illustration is gone), served from
    its own files: enlarged to 1920 with sharpening so wide screens don't stretch the 1280 photo (D-57)."""
    from PIL import Image

    from routes.public import HERO
    html = home.get_data(as_text=True)
    hero = html.split('class="hero"')[1].split("</section>")[0]
    tags = re.findall(r"<img\s[^>]*>", hero)
    assert len(tags) == 1 and "/images/hero/night-floodlights-" in tags[0]  # the photo the client picked
    assert 'loading="eager"' in tags[0] and 'fetchpriority="high"' in tags[0]
    assert "1920w" in tags[0] and 'width="1920"' in tags[0] and 'height="1440"' in tags[0]
    assert "Illustration" not in html and "hero-aerial" not in html
    for w in HERO["widths"]:
        with Image.open(STATIC / "images" / "hero" / f"night-floodlights-{w}.webp") as im:
            assert im.size == (w, w * 3 // 4) and not im.getexif()


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



def test_sticky_bar_reserves_scroll_space_on_mobile(client):
    """Regression (audit 2026-10-15): when the browser scrolls a form field or the Book now
    button into view (keyboard focus, phone keyboard 'Next'), it parked it right behind the
    fixed WhatsApp / Book now bar. scroll-padding-bottom keeps it above the bar."""
    css = client.get("/static/css/main.css").get_data(as_text=True)
    sticky = css.split("/* --------------------------------------------------- sticky mobile actions */")[1]
    assert re.search(r"@media \(max-width: 899px\) \{[^@]*scroll-padding-bottom", sticky)


# --- CR-12 design G: dark turf glow, giant name, gold actions -------------------

def test_dark_only_with_the_turf_glow_and_fonts(client):
    html = client.get("/").get_data(as_text=True)
    head = html.split("</head>")[0]
    assert "css/site.css" in head
    assert "Bebas+Neue" in head and "EB+Garamond" in head  # Google Fonts (D-56)
    assert 'class="turf-glow"' in html  # the fixed band of field-green light
    assert "tturf-theme" not in html and "data-theme-toggle" not in html  # one dark look, no switch


def test_admin_does_not_load_site_css(client):
    assert "site.css" not in client.get("/admin/login").get_data(as_text=True)


def test_prices_use_bangla_digits(client, app):
    with app.app_context():
        db.session.add(TurfSettings(id=1, turf_name="TTURFZONE",
                                    pricing={"morning": 1000, "afternoon": 1350, "night": 2000}))
        db.session.commit()
    section = client.get("/").get_data(as_text=True).split('id="pricing"')[1].split("</section>")[0]
    assert "১,০০০৳" in section and "১,৩৫০৳" in section and "২,০০০৳" in section


def test_hero_has_the_giant_name_and_live_line(home):
    html = home.get_data(as_text=True)
    assert html.count("<h1") == 1
    h1 = html.split("<h1")[1].split("</h1>")[0]
    assert "TTURFZONE" in h1 and "hero__name" in h1
    hero = html.split('class="hero"')[1].split("</section>")[0]
    assert "data-night-line" in hero  # "Night hours start in ..." in Dhaka time (main.js)
    assert "Book an hour" not in hero and "btn" not in hero  # the menu and the phone bar have Book (client, 2026-11-13)
    assert "hero__tagline" not in hero and "Book a one-hour slot online" not in hero  # dropped (client, 2026-11-13)
    assert "js/hero.js" not in html and "data-hero-slide" not in html


def test_footer_has_columns_facebook_and_the_wordmark(client):
    html = client.get("/").get_data(as_text=True)
    footer = html.split('class="site-footer"')[1]
    assert 'href="https://www.facebook.com/TTURFZONE"' in footer
    assert "tturfzone@gmail.com" in footer and "/privacy" in footer
    assert 'footer__word' in footer and 'aria-label="TTURFZONE"' in footer


# --- CR-12: the lower sections ------------------------------------------------------

def _section(html, section_id):
    return html.split(f'id="{section_id}"')[1].split("</section>")[0]


def test_section_titles(client):
    html = client.get("/").get_data(as_text=True)
    for title in ("Book your turf", "One day, 24 hours", "About our turf", "Why choose us",
                  "Good to know", "Find the ground"):
        assert title in html


def test_advance_band_only_when_online_booking_is_open(client, app):
    assert 'id="advance"' not in client.get("/").get_data(as_text=True)  # no bKash number yet
    with app.app_context():
        open_booking(advance_bdt=700)
    band = _section(client.get("/").get_data(as_text=True), "advance")
    assert "৳700" in band and "holds any hour" in band and "not refunded" in band


def test_good_to_know_states_the_booking_rules_of_the_site(client):
    faq = _section(client.get("/").get_data(as_text=True), "faq")
    for text in ("refunded", "TrxID", "1 AM", "Google", "email"):
        assert text in faq


def test_why_choose_us_from_settings(client, app):
    with app.app_context():
        db.session.add(TurfSettings(id=1, turf_name="TTURFZONE", facilities=[
            {"title": "Floodlights", "text": "LED lights for night games"},
            {"title": "Parking", "text": ""}]))
        db.session.commit()
    why = _section(client.get("/").get_data(as_text=True), "why")
    assert "Floodlights" in why and "LED lights for night games" in why and "Parking" in why
    assert "TODO" not in why


def test_why_choose_us_todo_in_development_when_empty(client):
    assert "C-32" in _section(client.get("/").get_data(as_text=True), "why")


def test_ground_rules_one_row_per_line(client, app):
    with app.app_context():
        db.session.add(TurfSettings(id=1, turf_name="TTURFZONE",
                                    booking_rules_text="No metal studs\n\nArrive 15 minutes early\n"))
        db.session.commit()
    html = client.get("/").get_data(as_text=True)
    rules = html.split('id="rules"')[1].split("</div>")[0]
    assert rules.count('class="rule"') == 2
    assert "No metal studs" in rules and "Arrive 15 minutes early" in rules


def test_contact_section_lists_email_and_location(client, app):
    with app.app_context():
        db.session.add(TurfSettings(id=1, turf_name="TTURFZONE", phone="01700000000", address="Notin Rani ghat"))
        db.session.commit()
    contact = _section(client.get("/").get_data(as_text=True), "contact")
    assert "tturfzone@gmail.com" in contact and "01700000000" in contact and "Notin Rani ghat" in contact


# --- the map before the footer (client, 2026-11-13) ------------------------------------------

MAP_LINK = "https://maps.app.goo.gl/aDJKZxWBbtHC5p6E7?g_st=aw"
MAP_EMBED = "https://www.google.com/maps/embed?origin=mfe&pb=!1m3!2m1!1sT+Turf+Zone,+2C42%2BWQ9,+Feni!6i17"


def test_map_section_sits_just_before_the_footer(client, app):
    with app.app_context():
        db.session.add(TurfSettings(id=1, turf_name="TTURFZONE", map_link=MAP_LINK, map_embed_url=MAP_EMBED))
        db.session.commit()
    html = client.get("/").get_data(as_text=True)
    section = html.split('id="map"')[1].split("</section>")[0]
    assert f'src="{MAP_EMBED.replace("&", "&amp;")}"' in section and 'title="Map to TTURFZONE"' in section
    assert f'href="{MAP_LINK.replace("&", "&amp;")}"' in section and "Open in Google Maps" in section
    after = html.split('id="map"')[1]
    assert after.index("</section>") < after.index('class="site-footer"')  # nothing else in between
    assert "</section>" not in after.split("</section>", 1)[1].split('class="site-footer"')[0]
    assert html.count("<iframe") == 1  # only here, not again in the Find the ground card


def test_no_map_section_without_an_embed_url(client):
    assert 'id="map"' not in client.get("/").get_data(as_text=True)
