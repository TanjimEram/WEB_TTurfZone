"""The one-time data migration that fills in the client's details (2026-11-13).

It sets the bKash merchant number, the three prices and the map on the existing
turf_settings row, but only where they are still empty: whatever the owner already
saved in Settings is never overwritten.
"""
from pathlib import Path

import pytest
from flask_migrate import upgrade
from sqlalchemy import text

from app import create_app
from extensions import db

MIGRATIONS = str(Path(__file__).resolve().parent.parent / "database" / "migrations")
BEFORE = "d5e1a7c3b9f2"


@pytest.fixture
def old_database(tmp_path):
    app = create_app("testing", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'site.db'}"})
    with app.app_context():
        upgrade(directory=MIGRATIONS, revision=BEFORE)
        yield app
        db.session.remove()
        db.engine.dispose()


REQUIRED = "booking_window_days, max_pending_per_phone, facilities, reviews, gallery, updated_at"
REQUIRED_VALUES = "14, 2, '[]', '[]', '[]', '2026-11-13 00:00:00'"


def _row():
    return db.session.execute(text(
        "SELECT bkash_number, pricing, map_link, map_embed_url FROM turf_settings WHERE id = 1")).one()


def test_fills_an_empty_settings_row(old_database):
    db.session.execute(text(f"INSERT INTO turf_settings (id, turf_name, bkash_number, pricing, map_link, {REQUIRED}) "
                            f"VALUES (1, 'TTURFZONE', '', '[]', 'TODO(owner): Google Maps pin link (C-07)', {REQUIRED_VALUES})"))
    db.session.commit()
    upgrade(directory=MIGRATIONS)
    bkash, pricing, link, embed = _row()
    assert bkash == "01827881299"
    assert '"morning": 1000' in pricing and '"afternoon": 1500' in pricing and '"night": 1800' in pricing
    assert link == "https://maps.app.goo.gl/aDJKZxWBbtHC5p6E7?g_st=aw"
    assert embed.startswith("https://www.google.com/maps/embed?") and "T+Turf+Zone" in embed


def test_never_overwrites_what_the_owner_saved(old_database):
    db.session.execute(text(f"INSERT INTO turf_settings (id, turf_name, bkash_number, pricing, map_link, map_embed_url, {REQUIRED}) "
                            "VALUES (1, 'TTURFZONE', '01999999999', '{\"morning\": 900, \"afternoon\": 900, \"night\": 900}', "
                            f"'https://maps.example/owner', 'https://www.google.com/maps?q=owner&output=embed', {REQUIRED_VALUES})"))
    db.session.commit()
    upgrade(directory=MIGRATIONS)
    bkash, pricing, link, embed = _row()
    assert bkash == "01999999999" and '"morning": 900' in pricing
    assert link == "https://maps.example/owner" and embed == "https://www.google.com/maps?q=owner&output=embed"


def test_does_nothing_without_a_settings_row(old_database):
    upgrade(directory=MIGRATIONS)  # a fresh install: seed-settings creates the row later
    assert db.session.execute(text("SELECT COUNT(*) FROM turf_settings")).scalar() == 0
