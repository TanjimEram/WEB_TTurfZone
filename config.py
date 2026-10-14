"""All configuration in one place.

Static settings live in the classes below. Values that differ per machine
(SECRET_KEY, DATABASE_URL) come from environment variables or the .env file,
and are applied in `app.create_app()`.
"""
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env if present. Real environment variables always win over .env values.
load_dotenv(BASE_DIR / ".env")


class BaseConfig:
    ENV_NAME = "base"
    SECRET_KEY = "dev-only-not-a-secret"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # test the connection before using it
        # MariaDB drops connections idle longer than wait_timeout (8 h by default, but
        # shared cPanel hosts often lower it to a few minutes). Recycling after 280 s stays
        # under any common value, and reconnecting to localhost costs about a millisecond.
        "pool_recycle": 280,
    }
    TIMEZONE = "Asia/Dhaka"
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    ENABLE_DEV_TOOLS = False  # /dev/wiring diagnostics page (plan D-18)
    PAYMENTS_ENABLED = False  # bKash advance (D-24); false = auto-confirm, no payment (CR-2/M4.6)
    SHOW_TODO_NOTES = True    # visible TODO(owner) notes for missing content; off in production (D-50)


class DevelopmentConfig(BaseConfig):
    ENV_NAME = "development"
    DEBUG = True
    ENABLE_DEV_TOOLS = True


class TestingConfig(BaseConfig):
    ENV_NAME = "testing"
    TESTING = True
    SECRET_KEY = "testing-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    ENV_NAME = "production"
    SESSION_COOKIE_SECURE = True
    SHOW_TODO_NOTES = False   # customers never see TODO notes; empty sections hide instead (D-50)


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def normalize_database_url(url: str) -> str:
    """Make hosting-provided URLs pick the driver we install.

    Production is MariaDB on the host (CR-4): `mysql://...` -> `mysql+pymysql://...`.
    PostgreSQL stays supported for a possible future move:
    `postgres://...` / `postgresql://...` -> `postgresql+psycopg://...` (psycopg 3).
    URLs that already name a driver (`mysql+pymysql://`, `sqlite://`) pass through unchanged.
    """
    for prefix, driver in (
        ("postgres://", "postgresql+psycopg://"),
        ("postgresql://", "postgresql+psycopg://"),
        ("mysql://", "mysql+pymysql://"),
    ):
        if url.startswith(prefix):
            return driver + url[len(prefix):]
    return url
