"""Google sign-in (CR-9, M4.9). Google is faked: services.google._post_form / _get_json."""
import logging
from urllib.parse import parse_qs, urlparse

import pytest

from services import google

STATE = "fixed-state-for-tests"
USER = {"sub": "1234", "email": "Player@Gmail.com", "email_verified": True, "name": "Rafi Ahmed"}


@pytest.fixture
def fake_google(monkeypatch):
    calls = {"token": [], "userinfo": []}

    def post_form(url, data):
        calls["token"].append((url, dict(data)))
        return {"access_token": "SECRET-TOKEN", "id_token": "SECRET-ID-TOKEN"}

    def get_json(url, token):
        calls["userinfo"].append((url, token))
        return dict(USER)

    monkeypatch.setattr(google, "_post_form", post_form)
    monkeypatch.setattr(google, "_get_json", get_json)
    return calls


def _start(client, next_url="/book?date=2026-11-12&slot=01:00"):
    with client.session_transaction() as sess:
        sess["oauth_state"] = STATE
        sess["oauth_next"] = next_url


def test_google_start_redirects_with_state_and_fixed_redirect_uri(client, app):
    resp = client.get("/auth/google?next=/book", headers={"Host": "localhost"})
    assert resp.status_code == 302
    url = urlparse(resp.headers["Location"])
    query = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert query["client_id"] == [app.config["GOOGLE_CLIENT_ID"]]
    assert query["redirect_uri"] == [app.config["SITE_URL"] + "/auth/google/callback"]
    assert query["scope"] == ["openid email profile"]
    with client.session_transaction() as sess:
        assert query["state"] == [sess["oauth_state"]] and len(sess["oauth_state"]) >= 20
        assert sess["oauth_next"] == "/book"


def test_google_start_moves_to_site_url_host(client):
    resp = client.get("/auth/google?next=/book", headers={"Host": "www.localhost"})
    assert resp.status_code == 302
    assert resp.headers["Location"] == "http://localhost/auth/google?next=/book"
    with client.session_transaction() as sess:
        assert "oauth_state" not in sess


def test_callback_signs_in_and_returns_to_next(client, fake_google, app):
    _start(client)
    resp = client.get(f"/auth/google/callback?state={STATE}&code=abc")
    assert resp.status_code == 302 and resp.headers["Location"] == "/book?date=2026-11-12&slot=01:00"
    with client.session_transaction() as sess:
        assert sess["customer"] == {"sub": "1234", "email": "player@gmail.com", "name": "Rafi Ahmed"}
        assert "oauth_state" not in sess
    token_url, data = fake_google["token"][0]
    assert token_url == google.TOKEN_URL
    assert data["code"] == "abc" and data["grant_type"] == "authorization_code"
    assert data["redirect_uri"] == app.config["SITE_URL"] + "/auth/google/callback"


def test_callback_with_wrong_state_is_refused(client, fake_google):
    _start(client)
    resp = client.get("/auth/google/callback?state=someone-elses&code=abc", follow_redirects=True)
    assert "Couldn" in resp.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "customer" not in sess
    assert fake_google["token"] == []  # never exchanged


def test_unverified_google_email_is_refused(client, fake_google, monkeypatch):
    monkeypatch.setattr(google, "_get_json", lambda url, token: {**USER, "email_verified": False})
    _start(client)
    resp = client.get(f"/auth/google/callback?state={STATE}&code=abc", follow_redirects=True)
    assert "Couldn" in resp.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "customer" not in sess


def test_google_cancel_shows_message(client):
    _start(client)
    resp = client.get(f"/auth/google/callback?state={STATE}&error=access_denied", follow_redirects=True)
    assert "Google sign-in was cancelled." in resp.get_data(as_text=True)


def test_google_network_failure_shows_message(client, monkeypatch):
    def boom(url, data):
        raise google.GoogleError("token request failed")
    monkeypatch.setattr(google, "_post_form", boom)
    _start(client)
    resp = client.get(f"/auth/google/callback?state={STATE}&code=abc", follow_redirects=True)
    assert "Couldn't sign in with Google. Please try again." in resp.get_data(as_text=True).replace("&#39;", "'")


def test_offsite_next_is_ignored(client, fake_google):
    client.get("/auth/google?next=https://evil.example/", headers={"Host": "localhost"})
    with client.session_transaction() as sess:
        sess["oauth_state"] = STATE
    resp = client.get(f"/auth/google/callback?state={STATE}&code=abc")
    assert resp.headers["Location"] == "/book"


def test_logout_removes_the_customer_only(client):
    with client.session_transaction() as sess:
        sess["customer"] = {"sub": "1", "email": "a@b.test", "name": "A"}
        sess["something_else"] = 1
    assert client.post("/auth/logout").status_code == 302
    with client.session_transaction() as sess:
        assert "customer" not in sess and sess["something_else"] == 1


def test_login_page_offers_google(client):
    html = client.get("/login?next=/book").get_data(as_text=True)
    assert "Continue with Google" in html and "/auth/google?next=/book" in html.replace("%2F", "/")


def test_login_page_without_client_id_says_not_set_up(client, app):
    app.config["GOOGLE_CLIENT_ID"] = ""
    html = client.get("/login").get_data(as_text=True)
    assert "Continue with Google" not in html and "isn" in html and "set up" in html


def test_nav_shows_sign_in_or_the_customer(client):
    assert "/login" in client.get("/").get_data(as_text=True)
    with client.session_transaction() as sess:
        sess["customer"] = {"sub": "1", "email": "a@b.test", "name": "Rafi Ahmed"}
    html = client.get("/").get_data(as_text=True)
    assert "Rafi Ahmed" in html and "/auth/logout" in html


def test_privacy_page_lists_what_is_collected(client):
    html = client.get("/privacy").get_data(as_text=True)
    for item in ("Google", "email", "phone", "bKash", "transaction ID", "tturfzone@gmail.com"):
        assert item in html


def test_tokens_never_logged(client, fake_google, caplog):
    caplog.set_level(logging.DEBUG)
    _start(client)
    client.get(f"/auth/google/callback?state={STATE}&code=abc")
    assert "SECRET-TOKEN" not in caplog.text and "SECRET-ID-TOKEN" not in caplog.text
