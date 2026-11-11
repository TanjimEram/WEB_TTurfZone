"""Owner confirms or rejects a bKash payment; the customer is emailed via the Gmail API (CR-9, M5.11).

Google is never called: services.booking_emails.send_email or services.google's
network helpers are replaced in every test.
"""
import base64
import datetime as dt
import email

import pytest
from click.testing import CliRunner

import cli
from extensions import db
from models import Booking, TurfSettings
from services import google, mailer
from services.booking_emails import booking_email
from services.bookings import create_booking_request
from services.slots import current_operating_day
from tests.test_admin_routes import admin_user, as_admin  # noqa: F401  (fixtures)

DAY = current_operating_day() + dt.timedelta(days=3)


@pytest.fixture
def outbox(app, monkeypatch):
    sent = []
    monkeypatch.setattr("services.booking_emails.send_email",
                        lambda to, subject, body: sent.append({"to": to, "subject": subject, "body": body}))
    app.config.update(GMAIL_REFRESH_TOKEN="test-refresh-token", MAIL_FROM="TTURFZONE <tturfzone@gmail.com>")
    return sent


@pytest.fixture(autouse=True)
def _fresh_token_cache():
    google._gmail_token.clear()
    yield
    google._gmail_token.clear()


def _pending(app, slot=dt.time(19), trx="8N7A6D5E4F"):
    with app.app_context():
        b = create_booking_request("Rafi Ahmed", "01712345678", DAY, slot,
                                   email="player@gmail.com", payer_number="01812345678", trx_id=trx)
        return b.id


def _get(app, booking_id):
    with app.app_context():
        return db.session.get(Booking, booking_id)


# --- admin actions -----------------------------------------------------------

def test_confirm_sends_confirmation_email(as_admin, app, outbox):  # noqa: F811
    bid = _pending(app)
    resp = as_admin.post(f"/admin/bookings/{bid}/confirm", follow_redirects=True)
    assert "Email sent to player@gmail.com" in resp.get_data(as_text=True)
    b = _get(app, bid)
    assert b.status == Booking.CONFIRMED and b.email_sent_at is not None
    assert len(outbox) == 1 and outbox[0]["to"] == "player@gmail.com"
    assert "confirmed" in outbox[0]["subject"].lower() and b.booking_code in outbox[0]["body"]


def test_reject_sends_rejection_email_and_frees_slot(as_admin, app, outbox):  # noqa: F811
    bid = _pending(app)
    as_admin.post(f"/admin/bookings/{bid}/reject")
    assert _get(app, bid).status == Booking.REJECTED
    assert len(outbox) == 1 and "8N7A6D5E4F" in outbox[0]["body"]
    assert "confirmed" not in outbox[0]["subject"].lower()
    _pending(app, trx="TRX0000002")  # the same slot can be booked again


def test_confirm_survives_email_failure_and_offers_resend(as_admin, app, outbox, monkeypatch):  # noqa: F811
    def broken(to, subject, body):
        raise google.GoogleError("Google answered HTTP 401")
    monkeypatch.setattr("services.booking_emails.send_email", broken)
    bid = _pending(app)
    resp = as_admin.post(f"/admin/bookings/{bid}/confirm", follow_redirects=True)
    html = resp.get_data(as_text=True).replace("&#39;", "'")
    assert "Confirmed, but the email couldn't be sent" in html
    b = _get(app, bid)
    assert b.status == Booking.CONFIRMED and b.email_sent_at is None
    assert "Resend email" in as_admin.get("/admin/bookings").get_data(as_text=True)


def test_resend_email_sends_again_and_hides_button(as_admin, app, outbox, monkeypatch):  # noqa: F811
    bid = _pending(app)
    with app.app_context():
        db.session.get(Booking, bid).status = Booking.CONFIRMED
        db.session.commit()
    assert "Resend email" in as_admin.get("/admin/bookings").get_data(as_text=True)
    as_admin.post(f"/admin/bookings/{bid}/email")
    assert len(outbox) == 1 and _get(app, bid).email_sent_at is not None
    assert "Resend email" not in as_admin.get("/admin/bookings").get_data(as_text=True)


def test_resend_refuses_a_pending_booking(as_admin, app, outbox):  # noqa: F811
    bid = _pending(app)
    as_admin.post(f"/admin/bookings/{bid}/email")
    assert outbox == []


def test_resend_requires_login(client, app, outbox):
    bid = _pending(app)
    resp = client.post(f"/admin/bookings/{bid}/email")
    assert resp.status_code == 302 and "/admin/login" in resp.headers["Location"]
    assert outbox == []


def test_dashboard_lists_payments_to_check_first(as_admin, app):  # noqa: F811
    _pending(app)
    html = as_admin.get("/admin/").get_data(as_text=True)
    assert "Payments to check" in html
    to_check = html.split("Payments to check")[1].split("Bookings today")[0]
    for text in ("8N7A6D5E4F", "01812345678", "Rafi Ahmed", "Confirm", "Reject"):
        assert text in to_check


def test_bookings_list_shows_payment_details(as_admin, app):  # noqa: F811
    _pending(app)
    html = as_admin.get("/admin/bookings").get_data(as_text=True)
    assert "8N7A6D5E4F" in html and "01812345678" in html and "player@gmail.com" in html


# --- the email itself --------------------------------------------------------

def test_confirmation_email_has_code_date_time_and_balance(app):
    db.session.add(TurfSettings(id=1, turf_name="TTURFZONE", pricing={"morning": 1000, "afternoon": 1350, "night": 2000},
                                advance_bdt=500, phone="01700000000"))
    db.session.commit()
    b = create_booking_request("Rafi Ahmed", "01712345678", DAY + dt.timedelta(days=1), dt.time(1),
                               email="player@gmail.com", payer_number="01812345678", trx_id="8N7A6D5E4F")
    b.status = Booking.CONFIRMED
    subject, body = booking_email(b, TurfSettings.current())
    assert b.booking_code in subject + body
    assert f"{b.booking_date:%a %d %b %Y}" in body and "01:00 AM" in body and "02:00 AM" in body
    assert "৳500" in body and "৳1,500" in body  # night price 2000 - advance 500 due at the ground
    assert "01700000000" in body


# --- Gmail transport ---------------------------------------------------------

def test_gmail_send_refreshes_and_caches_token(app, monkeypatch):
    app.config["GMAIL_REFRESH_TOKEN"] = "test-refresh-token"
    token_calls, sends = [], []
    monkeypatch.setattr(google, "_post_form", lambda url, data: token_calls.append(data) or
                        {"access_token": "ACCESS-1", "expires_in": 3599})
    monkeypatch.setattr(google, "_post_json", lambda url, token, payload: sends.append((url, token, payload)) or {"id": "m"})
    google.gmail_send(b"Subject: hi\r\n\r\nbody")
    google.gmail_send(b"Subject: again\r\n\r\nbody")
    assert len(token_calls) == 1 and token_calls[0]["grant_type"] == "refresh_token"
    assert token_calls[0]["refresh_token"] == "test-refresh-token"
    assert [s[1] for s in sends] == ["ACCESS-1", "ACCESS-1"]
    assert sends[0][0] == google.GMAIL_SEND_URL
    assert base64.urlsafe_b64decode(sends[0][2]["raw"]) == b"Subject: hi\r\n\r\nbody"


def test_gmail_send_failure_raises_without_secrets(app, monkeypatch):
    app.config["GMAIL_REFRESH_TOKEN"] = "test-refresh-token"
    monkeypatch.setattr(google, "_post_form", lambda url, data: {"access_token": "ACCESS-1", "expires_in": 3599})

    def refused(url, token, payload):
        raise google.GoogleError("Google answered HTTP 401")
    monkeypatch.setattr(google, "_post_json", refused)
    with pytest.raises(google.GoogleError) as exc:
        google.gmail_send(b"x")
    assert "ACCESS-1" not in str(exc.value) and "test-refresh-token" not in str(exc.value)
    assert google._gmail_token == {}  # a refused token is dropped, the next send fetches a new one


def test_mailer_prefers_gmail_when_refresh_token_set(app, monkeypatch):
    app.config.update(GMAIL_REFRESH_TOKEN="test-refresh-token", MAIL_FROM="TTURFZONE <tturfzone@gmail.com>",
                      MAIL_SERVER="")
    raws = []
    monkeypatch.setattr(google, "gmail_send", raws.append)
    assert mailer.mail_configured()
    mailer.send_email("player@gmail.com", "Hello", "Body text")
    message = email.message_from_bytes(raws[0])
    assert message["To"] == "player@gmail.com" and message["Subject"] == "Hello"
    assert "tturfzone@gmail.com" in message["From"]


def test_gmail_authorize_prints_refresh_token(app, monkeypatch):
    monkeypatch.setattr(cli, "_open_browser", lambda url: None)
    monkeypatch.setattr(cli, "_wait_for_gmail_code", lambda state: {"code": "CODE-1", "state": state})
    monkeypatch.setattr(google, "refresh_token_from_code", lambda code: "REFRESH-XYZ" if code == "CODE-1" else "")
    result = CliRunner().invoke(cli.gmail_authorize, obj=None, catch_exceptions=False,
                                standalone_mode=False, args=[], env={})
    assert "REFRESH-XYZ" in result.output and "GMAIL_REFRESH_TOKEN" in result.output


def test_gmail_authorize_refuses_a_wrong_state(app, monkeypatch):
    monkeypatch.setattr(cli, "_open_browser", lambda url: None)
    monkeypatch.setattr(cli, "_wait_for_gmail_code", lambda state: {"code": "CODE-1", "state": "not-it"})
    monkeypatch.setattr(google, "refresh_token_from_code", lambda code: "REFRESH-XYZ")
    result = CliRunner().invoke(cli.gmail_authorize, args=[])
    assert result.exit_code != 0 and "REFRESH-XYZ" not in result.output
