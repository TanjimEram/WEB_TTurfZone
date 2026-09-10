import pytest

from app import create_app
from extensions import db
from models import Booking


@pytest.fixture
def dev_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    app = create_app("development", overrides={"WTF_CSRF_ENABLED": False})
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def test_wiring_page_shows_database_status(dev_client):
    page = dev_client.get("/dev/wiring").get_data(as_text=True)
    assert "sqlite" in page
    assert "Connected" in page


def test_wiring_buttons_create_and_clear_fake_bookings(dev_client):
    dev_client.post("/dev/fake-bookings", follow_redirects=True)
    assert Booking.query.count() == 10
    page = dev_client.post("/dev/double-booking", follow_redirects=True).get_data(as_text=True)
    assert "caught" in page
    dev_client.post("/dev/clear-fake", follow_redirects=True)
    assert Booking.query.count() == 0
