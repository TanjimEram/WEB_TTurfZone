"""Real PostgreSQL checks. Run with:  TEST_DATABASE_URL=... pytest -m postgres

WARNING: point TEST_DATABASE_URL at a throwaway database or Neon branch. These tests drop every table.
"""
import threading
from datetime import date, time

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import text

from app import create_app
from config import normalize_database_url
from extensions import db
from models import Booking
from services.bookings import SlotUnavailableError, generate_booking_code, save_booking
from services.fake_data import try_double_booking

pytestmark = pytest.mark.postgres


def _reset(app):
    with app.app_context():
        db.drop_all()
        db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
        db.session.commit()


@pytest.fixture
def pg_app(pg_url):
    app = create_app("testing", overrides={
        "SQLALCHEMY_DATABASE_URI": normalize_database_url(pg_url),
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True, "pool_size": 12, "max_overflow": 0},
    })
    _reset(app)
    with app.app_context():
        upgrade()  # runs the real migrations, same as production
    yield app
    _reset(app)
    with app.app_context():
        db.engine.dispose()  # close pooled connections so tests leave nothing open


def test_migrations_create_partial_unique_index(pg_app):
    with pg_app.app_context():
        indexdef = db.session.execute(text(
            "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_active_slot'"
        )).scalar_one()
    assert "UNIQUE" in indexdef and "WHERE" in indexdef


def test_database_catches_double_booking(pg_app):
    with pg_app.app_context():
        assert try_double_booking()["conflict_caught"] is True


def test_only_one_of_ten_simultaneous_requests_gets_the_slot(pg_app):
    barrier = threading.Barrier(10)
    results = []
    lock = threading.Lock()

    def attempt(n):
        with pg_app.app_context():
            booking = Booking(booking_code=generate_booking_code(), customer_name=f"Racer {n}",
                              phone="01700000000", booking_date=date(2030, 5, 5),
                              slot_time=time(19, 30), status=Booking.PENDING)
            barrier.wait()
            try:
                save_booking(booking)
                outcome = "ok"
            except SlotUnavailableError:
                outcome = "taken"
            finally:
                db.session.remove()
            with lock:
                results.append(outcome)

    threads = [threading.Thread(target=attempt, args=(n,)) for n in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("ok") == 1
    assert results.count("taken") == 9


def test_migrations_downgrade_cleanly(pg_app):
    with pg_app.app_context():
        downgrade(revision="base")
        tables = db.session.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )).scalars().all()
    assert "bookings" not in tables
