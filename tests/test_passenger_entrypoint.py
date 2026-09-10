"""Simulates how cPanel's Passenger loads the app: import passenger_wsgi.application."""
import importlib
import sys

from werkzeug.test import Client


def test_passenger_entrypoint_serves_healthz_in_production_mode(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "y" * 64)
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    sys.modules.pop("passenger_wsgi", None)
    module = importlib.import_module("passenger_wsgi")
    response = Client(module.application).get("/healthz")
    assert response.status_code == 200
    assert response.get_data(as_text=True) == "ok"
