"""Database diagnostics used by `flask db-check` and /dev/wiring."""
from time import perf_counter

from sqlalchemy import inspect, text

from extensions import db

REQUIRED_TABLES = ("admins", "bookings", "turf_settings")


def check_database() -> dict:
    """Connect, measure a round trip, and check tables and migration version. Never raises."""
    url = db.engine.url
    result = {
        "ok": False,
        "connected": False,
        "dialect": url.get_backend_name(),
        "host": url.host or "local file",
        "database": url.database or "in-memory",
        "latency_ms": None,
        "missing_tables": list(REQUIRED_TABLES),
        "migration_revision": None,
        "error": None,
    }
    try:
        started = perf_counter()
        db.session.execute(text("SELECT 1"))
        result["latency_ms"] = round((perf_counter() - started) * 1000, 1)
        result["connected"] = True

        tables = set(inspect(db.engine).get_table_names())
        result["missing_tables"] = [t for t in REQUIRED_TABLES if t not in tables]
        if "alembic_version" in tables:
            result["migration_revision"] = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        result["ok"] = not result["missing_tables"]
    except Exception as exc:  # report, don't crash: this is a diagnostics tool
        db.session.rollback()
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result
