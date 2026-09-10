"""Friendly 404 / 500 pages (M7.5). No stack traces, working links."""
import pytest

from app import create_app
from extensions import db


def test_404_is_friendly(client):
    resp = client.get("/no-such-page")
    assert resp.status_code == 404
    html = resp.get_data(as_text=True)
    assert "can't find that page" in html
    assert 'href="/"' in html
    assert "Traceback" not in html


@pytest.fixture
def boom_client():
    app = create_app("testing", overrides={"PROPAGATE_EXCEPTIONS": False})

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def test_500_is_friendly(boom_client):
    resp = boom_client.get("/boom")
    assert resp.status_code == 500
    html = resp.get_data(as_text=True)
    assert "Something went wrong" in html
    assert "kaboom" not in html
    assert "Traceback" not in html
