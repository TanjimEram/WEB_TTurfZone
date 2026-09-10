import pytest
from sqlalchemy import event

from app import create_app
from extensions import db


def test_blueprints_are_registered(app):
    assert {"public", "api", "admin"} <= set(app.blueprints)


def test_healthz_returns_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"


def test_healthz_does_not_query_the_database(app, client):
    statements = []

    def count(*args, **kwargs):
        statements.append(1)

    event.listen(db.engine, "before_cursor_execute", count)
    try:
        client.get("/healthz")
    finally:
        event.remove(db.engine, "before_cursor_execute", count)
    assert statements == []


def test_homepage_loads(client):
    assert client.get("/").status_code == 200


def test_security_headers_are_set(client):
    headers = client.get("/healthz").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_production_refuses_to_start_without_secrets(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


def test_production_has_no_dev_tools(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 64)
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    prod = create_app("production")
    assert "dev" not in prod.blueprints
    assert prod.config["SESSION_COOKIE_SECURE"] is True
    assert prod.test_client().get("/dev/wiring").status_code == 404


def test_development_has_dev_tools(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    assert "dev" in create_app("development").blueprints
