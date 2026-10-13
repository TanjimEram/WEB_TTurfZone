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
