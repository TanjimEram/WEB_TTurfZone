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
        "pool_recycle": 280,     # Neon closes idle connections; reconnect before that
    }
    TIMEZONE = "Asia/Dhaka"
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    ENABLE_DEV_TOOLS = False  # /dev/wiring diagnostics page (plan D-18)


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


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def normalize_database_url(url: str) -> str:
    """Make hosting-provided URLs work with SQLAlchemy + psycopg 3.

    Neon, Render and cPanel give URLs like `postgresql://...` or `postgres://...`.
    SQLAlchemy needs `postgresql+psycopg://...` to pick the psycopg 3 driver.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url
