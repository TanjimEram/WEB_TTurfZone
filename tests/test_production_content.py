"""D-50: in production, customers never see TODO(owner) notes; empty sections hide with their links."""
import re
from datetime import timedelta

import pytest

from app import create_app
from extensions import db
from models import TurfSettings
from services.slots import today_dhaka

PUBLIC_PAGES = ["/", "/book"]
ALL = ["06:00", "07:30", "09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30"]


@pytest.fixture
def prod_client():
    """Testing app with production's content behaviour (SHOW_TODO_NOTES off)."""
    app = create_app("testing", overrides={"SHOW_TODO_NOTES": False})
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def _dead_hash_links(html):
    targets = set(re.findall(r'href="(?:/)?#([\w-]+)"', html))
    return sorted(t for t in targets if f'id="{t}"' not in html)


def test_production_config_hides_todo_notes():
    from config import ProductionConfig, TestingConfig
    assert ProductionConfig.SHOW_TODO_NOTES is False
    assert TestingConfig.SHOW_TODO_NOTES is True  # developers still see every gap


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_no_todo_notes_on_public_pages(prod_client, path):
    html = prod_client.get(path).get_data(as_text=True)
    assert "TODO" not in html and "todo-note" not in html
    assert not re.search(r'btn--whatsapp"[^>]*aria-disabled', html)  # no greyed-out WhatsApp buttons


def test_success_page_has_no_todo(prod_client):
    day = (today_dhaka() + timedelta(days=3)).isoformat()
    prod_client.post("/book", data={"name": "Rafi", "phone": "01712345678", "date": day, "slot": "18:00"})
    html = prod_client.get("/book/success").get_data(as_text=True)
    assert "Booking confirmed" in html and "TODO" not in html


def test_empty_sections_and_their_links_are_hidden(prod_client):
    html = prod_client.get("/").get_data(as_text=True)
    for section in ("pricing", "location", "reviews"):
        assert f'id="{section}"' not in html
        assert f"#{section}" not in html
    assert _dead_hash_links(html) == []
    assert "Book a 90-minute slot online and get confirmed instantly." in html  # neutral hero line
    assert "WhatsApp" not in html.split('class="hero__actions"')[1].split("</div>")[0]  # no dead button
    assert 'id="gallery"' in html and 'id="about"' in html and 'id="facebook"' in html


def test_sections_come_back_once_the_owner_adds_content(prod_client):
    db.session.add(TurfSettings(
        turf_name="TTURFZONE", tagline="Floodlit six-a-side", address="Notin Rani ghat",
        default_price_bdt=4000, whatsapp="8801712345678",
        pricing=[{"label": "Flat", "slots": ALL, "days": "all", "price_bdt": 4000}],
        reviews=[{"text": "Great pitch", "name": "Real Customer"}],
    ))
    db.session.commit()
    html = prod_client.get("/").get_data(as_text=True)
    for section in ("pricing", "location", "reviews"):
        assert f'id="{section}"' in html and f"#{section}" in html
    assert "Floodlit six-a-side" in html and "৳4,000" in html and "wa.me/8801712345678" in html
    assert "TODO" not in html and _dead_hash_links(html) == []


def test_slot_span_follows_the_owner_slot_times(prod_client):
    db.session.add(TurfSettings(turf_name="T", slot_times=["05:30"] + ALL[1:]))
    db.session.commit()
    assert "Fixed slots, 05:30 AM to 12:00 AM." in prod_client.get("/").get_data(as_text=True)
