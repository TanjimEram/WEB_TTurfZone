"""Real MariaDB checks (production engine, CR-4). Run with:  pytest -m mariadb

TEST_DATABASE_URL=mysql+pymysql://user:pass@127.0.0.1:3307/tturf_test?charset=utf8mb4
WARNING: point it at a THROWAWAY database. These tests drop every table.
Use MariaDB 11.4 (production), not MySQL: generated-column behaviour differs.
"""
import threading
from datetime import date, datetime, time, timedelta, timezone

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import create_app
from config import normalize_database_url
from extensions import db
from models import Booking, TurfSettings
from services.bookings import SlotUnavailableError, generate_booking_code, save_booking

pytestmark = pytest.mark.mariadb

DAY = date(2030, 5, 5)
SLOT = time(19, 30)
BANGLA = "টি টার্ফ জোন — রাফি আহমেদ"


def _reset(app):
    with app.app_context():
        db.drop_all()
        db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
        db.session.commit()


@pytest.fixture
def maria_app(mariadb_url):
    app = create_app("testing", overrides={
        "SQLALCHEMY_DATABASE_URI": normalize_database_url(mariadb_url),
        "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True, "pool_size": 12, "max_overflow": 0},
    })
    _reset(app)
    with app.app_context():
        upgrade()  # the real migrations, same as production
    yield app
    _reset(app)
    with app.app_context():
        db.engine.dispose()


def _booking(status=Booking.CONFIRMED, code=None, name="Rafi"):
    return Booking(booking_code=code or generate_booking_code(), customer_name=name,
                   phone="01712345678", booking_date=DAY, slot_time=SLOT, status=status)


def _assert_slot_rule_in_place():
    """active_slot_key is a STORED generated column with a unique index; no WHERE-less uq_active_slot."""
    col = db.session.execute(text(
        "SELECT IS_GENERATED, EXTRA, GENERATION_EXPRESSION FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'bookings' AND COLUMN_NAME = 'active_slot_key'"
    )).one()
    assert col.IS_GENERATED == "ALWAYS"
    assert col.EXTRA == "STORED GENERATED"
    expr = col.GENERATION_EXPRESSION.lower()
    assert "case when" in expr and "concat" in expr
    assert "'pending','confirmed','blocked'" in expr.replace(" ", "")

    indexes = db.session.execute(text(
        "SELECT INDEX_NAME, NON_UNIQUE, COLUMN_NAME FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'bookings'"
    )).all()
    assert ("uq_active_slot_key", 0, "active_slot_key") in [tuple(r) for r in indexes]
    assert "uq_active_slot" not in {r.INDEX_NAME for r in indexes}


def test_migration_builds_generated_column_and_unique_index(maria_app):
    with maria_app.app_context():
        _assert_slot_rule_in_place()


def test_create_all_builds_the_same_rule(maria_app):
    """Tests and scripts that use db.create_all() must get the same protection."""
    _reset(maria_app)
    with maria_app.app_context():
        db.create_all()
        _assert_slot_rule_in_place()


def test_tables_are_utf8mb4_and_lower_case(maria_app):
    with maria_app.app_context():
        rows = db.session.execute(text(
            "SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME <> 'alembic_version'"
        )).all()
    assert {r.TABLE_NAME for r in rows} == {"admins", "bookings", "login_failures", "turf_settings"}
    assert {r.TABLE_COLLATION for r in rows} == {"utf8mb4_unicode_ci"}
    # Linux MariaDB is case-sensitive about table names; every name we use is lower-case.
    assert all(name == name.lower() for name in db.metadata.tables)


@pytest.mark.parametrize("status", [Booking.PENDING, Booking.CONFIRMED, Booking.BLOCKED])
def test_active_statuses_hold_the_slot_and_rejected_frees_it(maria_app, status):
    with maria_app.app_context():
        holder = save_booking(_booking(status=status))
        with pytest.raises(SlotUnavailableError):
            save_booking(_booking(name="Second"))

        holder.status = Booking.REJECTED
        save_booking(holder)
        save_booking(_booking(name="Second"))  # slot is free again


def test_many_rejected_rows_can_share_a_slot(maria_app):
    """NULL keys don't collide, so released rows never block each other."""
    with maria_app.app_context():
        for n in range(3):
            save_booking(_booking(status=Booking.REJECTED, name=f"Old {n}"))
        save_booking(_booking(status=Booking.CONFIRMED))
        assert Booking.query.count() == 4


def test_duplicate_booking_code_is_not_reported_as_slot_taken(maria_app):
    with maria_app.app_context():
        save_booking(_booking(code="TZ-SAME01"))
        other = _booking(code="TZ-SAME01")
        other.booking_date = DAY + timedelta(days=1)
        with pytest.raises(IntegrityError) as exc:
            save_booking(other)
        assert not isinstance(exc.value, SlotUnavailableError)


def test_only_one_of_ten_simultaneous_requests_gets_the_slot(maria_app):
    barrier = threading.Barrier(10)
    results = []
    lock = threading.Lock()

    def attempt(n):
        with maria_app.app_context():
            booking = _booking(status=Booking.PENDING, name=f"Racer {n}")
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


def test_bangla_json_time_and_utc_round_trip(maria_app):
    with maria_app.app_context():
        before = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        save_booking(_booking(name=BANGLA))
        db.session.add(TurfSettings(id=1, turf_name="TTURFZONE", about_text=BANGLA,
                                    pricing=[{"label": "সকাল", "slots": ["06:00"], "days": "all", "price_bdt": 0}]))
        db.session.commit()
        db.session.expire_all()

        booking = Booking.query.one()
        settings = TurfSettings.query.one()
        assert booking.customer_name == BANGLA
        assert settings.about_text == BANGLA
        assert settings.pricing[0]["label"] == "সকাল"
        assert booking.slot_time == SLOT and isinstance(booking.slot_time, time)
        # DATETIME has no offset: values come back naive and are UTC by convention (models/_time.py).
        assert booking.created_at.tzinfo is None
        assert before - timedelta(seconds=1) <= booking.created_at <= before + timedelta(minutes=1)


def test_migrations_downgrade_cleanly(maria_app):
    with maria_app.app_context():
        downgrade(revision="base")
        tables = db.session.execute(text(
            "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
        )).scalars().all()
    assert set(tables) <= {"alembic_version"}


def test_lockout_and_reset_throttle_compare_utc_on_mariadb(maria_app, monkeypatch):
    """M5.10: both rules compare DATETIME columns in SQL; check they hold on the production engine."""
    from models import Admin, LoginFailure
    from services import auth

    sent = []
    monkeypatch.setattr(auth, "send_email", lambda to, subject, body: sent.append(to))
    with maria_app.test_request_context():
        db.session.add(Admin(username="owner", password_hash="x", email="owner@example.test"))
        db.session.add_all([LoginFailure(ip="203.0.113.5",
                                         created_at=datetime.now(timezone.utc) - timedelta(minutes=16))
                            for _ in range(5)])
        db.session.commit()
        assert not auth.is_locked_out("203.0.113.5")  # 16-minute-old failures have expired
        for _ in range(5):
            auth.record_login_failure("203.0.113.5")
        assert auth.is_locked_out("203.0.113.5")

        auth.send_reset_email("owner@example.test")
        auth.send_reset_email("owner@example.test")  # inside 5 minutes: nothing
        assert sent == ["owner@example.test"]


def test_trx_id_unique_on_mariadb(maria_app):
    """CR-9: one booking per bKash TrxID; blocks (no TrxID) are not limited."""
    with maria_app.app_context():
        save_booking(Booking(booking_code=generate_booking_code(), customer_name="A", phone="01711111111",
                             booking_date=DAY, slot_time=time(18), status=Booking.PENDING, trx_id="8N7A6D5E4F"))
        with pytest.raises(IntegrityError) as exc:
            save_booking(Booking(booking_code=generate_booking_code(), customer_name="B", phone="01722222222",
                                 booking_date=DAY, slot_time=time(19), status=Booking.PENDING, trx_id="8N7A6D5E4F"))
        assert "trx_id" in str(exc.value.orig)
        for hour in (20, 21):
            save_booking(Booking(booking_code=generate_booking_code(), booking_date=DAY, slot_time=time(hour),
                                 status=Booking.BLOCKED))
        assert db.session.scalar(db.select(db.func.count()).select_from(Booking)) == 3
