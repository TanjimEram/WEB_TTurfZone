"""Shared test fixtures.

Most tests run on an in-memory SQLite database, so they need nothing installed.
Tests marked @pytest.mark.postgres run only when TEST_DATABASE_URL is set.
"""
import os

import pytest

from app import create_app
from extensions import db as _db


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _test_db_url(*schemes):
    """TEST_DATABASE_URL if it points at this engine, else skip (one URL serves one marker)."""
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    if not url.startswith(schemes):
        pytest.skip(f"TEST_DATABASE_URL is not a {schemes[0]} URL")
    return url


@pytest.fixture
def pg_url():
    return _test_db_url("postgres://", "postgresql")


@pytest.fixture
def mariadb_url():
    return _test_db_url("mysql", "mariadb")


# --- CR-9 booking helpers: a signed-in Google customer and an open booking form ---

CUSTOMER = {"sub": "google-1", "email": "player@gmail.com", "name": "Rafi Ahmed"}
BKASH_NUMBER = "01827881299"


def sign_in(client, customer=None):
    """Put a Google customer in the test client's session (no Google involved)."""
    with client.session_transaction() as sess:
        sess["customer"] = dict(customer or CUSTOMER)
    return client


def open_booking(**fields):
    """Make sure turf_settings (id 1) has a bKash number, plus any other fields given.
    Call inside an app context."""
    from models import TurfSettings
    from database.seed_data import DEFAULT_SETTINGS
    row = TurfSettings.current()
    if row is None:
        row = TurfSettings(id=1, **DEFAULT_SETTINGS)
        _db.session.add(row)
    row.bkash_number = BKASH_NUMBER
    for key, value in fields.items():
        setattr(row, key, value)
    _db.session.commit()
    return row
