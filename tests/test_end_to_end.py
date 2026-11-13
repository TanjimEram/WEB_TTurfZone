"""End to end, the way production runs it (pre-handover audit, 2026-11-13).

CSRF protection is ON (TestingConfig turns it off for the other tests), the Google sign-in goes
through /auth/google and the callback, and booking emails go through the real mailer and
services.google.gmail_send. Only Google's three network helpers are faked (FakeGoogle), so no
test ever talks to Google.

Runs on SQLite in every `pytest -q`, and again on MariaDB with `pytest -q -m mariadb`.
"""
import base64
import html
import datetime as dt
import email
import os
import re
import threading
from datetime import timedelta
from email import policy

import pytest

from app import create_app
from extensions import db
from models import Admin, Booking, TurfSettings
from services import google
from services.slots import current_operating_day, operating_day

PRICES = {"morning": 1000, "afternoon": 1350, "night": 2000}
BKASH = "01827881299"
ALICE = {"sub": "g-alice", "email": "alice@gmail.com", "name": "Alice Rahman", "email_verified": True}
BOB = {"sub": "g-bob", "email": "bob@gmail.com", "name": "Bob Karim", "email_verified": True}
OWNER, OWNER_PASSWORD = "owner", "correct horse battery staple"


# --- a fake Google: sign-in codes, userinfo and the Gmail send endpoint ----------------------

class FakeGoogle:
    def __init__(self):
        self.profiles = {}      # sign-in code -> userinfo
        self.sent = []          # emails Gmail accepted: EmailMessage objects
        self.gmail_down = False

    def post_form(self, url, data):
        if data.get("grant_type") == "authorization_code":
            if data["code"] not in self.profiles:
                raise google.GoogleError("Google answered HTTP 400")
            return {"access_token": "access-" + data["code"]}
        if data.get("grant_type") == "refresh_token":
            return {"access_token": "gmail-access", "expires_in": 3600}
        raise AssertionError(f"unexpected form post to {url}")

    def get_json(self, url, token):
        assert url == google.USERINFO_URL
        return self.profiles[token.removeprefix("access-")]

    def post_json(self, url, token, payload):
        assert url == google.GMAIL_SEND_URL and token == "gmail-access"
        if self.gmail_down:
            raise google.GoogleError("Google answered HTTP 503")
        raw = base64.urlsafe_b64decode(payload["raw"])
        self.sent.append(email.message_from_bytes(raw, policy=policy.default))
        return {"id": f"msg-{len(self.sent)}"}

    def last(self, to):
        mails = [m for m in self.sent if m["To"] == to]
        assert mails, f"no email to {to}; sent: {[m['To'] for m in self.sent]}"
        return mails[-1]["Subject"], mails[-1].get_content()


def _engines():
    url = os.environ.get("TEST_DATABASE_URL", "")
    yield pytest.param("sqlite://", id="sqlite")
    yield pytest.param(url, id="mariadb", marks=[
        pytest.mark.mariadb,
        pytest.mark.skipif(not url.startswith(("mysql", "mariadb")), reason="TEST_DATABASE_URL is not MariaDB")])


@pytest.fixture(params=list(_engines()))
def site(request, monkeypatch):
    """The app as production runs it: CSRF on, Gmail sending, a seeded ground and an owner."""
    fake = FakeGoogle()
    monkeypatch.setattr(google, "_post_form", fake.post_form)
    monkeypatch.setattr(google, "_get_json", fake.get_json)
    monkeypatch.setattr(google, "_post_json", fake.post_json)
    google._gmail_token.clear()
    app = create_app("testing", {
        "SQLALCHEMY_DATABASE_URI": request.param,
        "WTF_CSRF_ENABLED": True,
        "MAIL_FROM": "TTURFZONE <tturfzone@gmail.com>",
        "GMAIL_REFRESH_TOKEN": "fake-refresh-token",
    })
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(TurfSettings(id=1, turf_name="TTURFZONE", bkash_number=BKASH, advance_bdt=500,
                                    pricing=PRICES, booking_window_days=14,
                                    booking_rules_text="Arrive 10 minutes early"))
        owner = Admin(username=OWNER, email="tturfzone@gmail.com")
        owner.set_password(OWNER_PASSWORD)
        db.session.add(owner)
        db.session.commit()
    # No app context stays pushed while requests run: each request gets its own, so Flask-WTF's
    # per-request CSRF cache can't leak between two visitors.
    yield app, fake
    with app.app_context():
        db.session.remove()
        db.drop_all()
    google._gmail_token.clear()


# --- helpers ---------------------------------------------------------------------------------

def token(client, path):
    page = client.get(path)
    assert page.status_code == 200, (path, page.status_code)
    return re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)).group(1)


def sign_in(client, fake, profile, next_path="/book"):
    """The real Google round trip: /auth/google -> Google -> /auth/google/callback."""
    fake.profiles["code-" + profile["sub"]] = profile
    start = client.get(f"/auth/google?next={next_path}")
    assert start.status_code == 302 and start.location.startswith(google.AUTH_URL)
    state = re.search(r"state=([^&]+)", start.location).group(1)
    return client.get(f"/auth/google/callback?state={state}&code=code-{profile['sub']}")


def signed_out(client):
    """The booking page offers a Google sign-in instead of naming the customer (CR-13)."""
    return "won't get an email" in client.get("/book").get_data(as_text=True)


def night(hour, days_ahead=1):
    """(real date, "HH:MM") of an hour in the night period, `days_ahead` operating days from now."""
    day = current_operating_day() + timedelta(days=days_ahead)
    real = day + timedelta(days=1) if hour < 6 else day
    return real.isoformat(), f"{hour:02d}:00"


def book(client, when, trx, *, phone="01712345678", payer="01712345678", no_refund="1", csrf=True):
    date, slot = when
    data = {"name": "Player", "phone": phone, "payer_number": payer, "trx_id": trx,
            "no_refund": no_refund, "date": date, "slot": slot}
    if csrf:
        data["csrf_token"] = token(client, f"/book?date={date}&slot={slot}")
    return client.post("/book", data=data)


def state_of(client, when):
    """The public availability state of one slot. The API takes the operating day."""
    date, slot = when
    day = operating_day(dt.date.fromisoformat(date), dt.time.fromisoformat(slot))
    slots = client.get(f"/api/availability?date={day.isoformat()}").get_json()["slots"]
    return next(s["state"] for s in slots if s["date"] == date and s["time"] == slot)


def owner_login(client, password=OWNER_PASSWORD):
    return client.post("/admin/login", data={"csrf_token": token(client, "/admin/login"),
                                             "username": OWNER, "password": password})


def booking_row(app, trx):
    with app.app_context():
        return db.session.scalar(db.select(Booking).where(Booking.trx_id == trx))


def admin_post(client, path, back="/admin/bookings", **fields):
    """POST an admin action with its CSRF token; the text of the page it lands on (flash included)."""
    response = client.post(path, data={"csrf_token": token(client, "/admin/bookings"), "back": back, **fields},
                           follow_redirects=True)
    return html.unescape(response.get_data(as_text=True))


def page_text(client, path):
    return html.unescape(client.get(path).get_data(as_text=True))


# --- 1. sign-in, sign-out --------------------------------------------------------------------

def test_sign_in_with_google_and_sign_out(site):
    app, fake = site
    alice = app.test_client()

    gate = alice.get("/book")
    assert gate.status_code == 200 and "won't get an email" in gate.get_data(as_text=True)  # sign-in optional (CR-13)
    assert "Continue with Google" in alice.get("/login?next=/book").get_data(as_text=True)

    start = alice.get("/auth/google?next=/book")
    assert "redirect_uri=http%3A%2F%2Flocalhost%2Fauth%2Fgoogle%2Fcallback" in start.location  # from SITE_URL
    assert "scope=openid+email+profile" in start.location

    # another host is moved to SITE_URL's host first (the state cookie lives there)
    moved = app.test_client().get("/auth/google?next=/book", base_url="http://www.localhost")
    assert moved.status_code == 302 and moved.location.startswith("http://localhost/auth/google")

    # a forged state, a cancelled consent and an unverified email are all refused
    alice.get("/auth/google?next=/book")
    fake.profiles["code-x"] = ALICE
    assert alice.get("/auth/google/callback?state=forged&code=code-x").status_code == 302
    assert signed_out(alice)
    alice.get("/auth/google?next=/book")
    alice.get("/auth/google/callback?error=access_denied&state=x")
    assert signed_out(alice)
    sign_in(alice, fake, {**ALICE, "sub": "g-unverified", "email_verified": False})
    assert signed_out(alice)

    done = sign_in(alice, fake, ALICE)
    assert done.status_code == 302 and done.location.endswith("/book")
    page = alice.get("/book").get_data(as_text=True)
    assert ALICE["email"] in page and "Sign out" in page

    assert alice.post("/auth/logout").status_code == 400  # no CSRF token
    out = alice.post("/auth/logout", data={"csrf_token": token(alice, "/book")})
    assert out.status_code == 302
    assert signed_out(alice)


# --- 2. booking: held while the payment is checked --------------------------------------------

def test_booking_holds_the_slot_until_the_owner_acts(site):
    app, fake = site
    alice, bob = app.test_client(), app.test_client()
    sign_in(alice, fake, ALICE)
    sign_in(bob, fake, BOB)
    seven = night(19)

    assert book(alice, seven, "TRXALICE01", csrf=False).status_code == 400  # CSRF required
    assert "advance isn't refunded" in book(alice, seven, "TRXALICE01", no_refund="").get_data(as_text=True)
    bad = book(alice, seven, "TRXALICE01", phone="12345")
    assert bad.status_code == 400 and booking_row(app, "TRXALICE01") is None

    ok = book(alice, seven, "trxalice01")  # lower case on purpose: stored upper case
    assert ok.status_code == 302 and ok.location.endswith("/book/success")
    success = alice.get("/book/success").get_data(as_text=True)
    assert "Payment being checked" in success and "TRXALICE01" in success and ALICE["email"] in success
    assert alice.get("/book/success").status_code == 302  # one-time page

    row = booking_row(app, "TRXALICE01")
    assert row.status == Booking.PENDING and row.customer_email == ALICE["email"]  # email from Google
    assert state_of(bob, seven) == "pending"  # held for everyone else

    taken = book(bob, seven, "TRXBOB0001")
    assert taken.status_code == 409 and "just taken" in taken.get_data(as_text=True)
    reused = book(bob, night(20), " trxalice01 ")  # someone else's TrxID, spaces and case changed
    assert reused.status_code == 400 and "already been used" in reused.get_data(as_text=True)

    api = bob.get(f"/api/availability?date={current_operating_day() + timedelta(days=1)}").get_data(as_text=True)
    for private in (ALICE["email"], "Player", "01712345678", "TRXALICE01"):
        assert private not in api  # the public API never shows who booked


def test_two_customers_racing_for_one_slot(site):
    app, fake = site
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        pytest.skip("an in-memory SQLite database can't be shared between threads; MariaDB runs this")
    clients = [app.test_client() for _ in range(6)]
    for i, c in enumerate(clients):
        sign_in(c, fake, {**ALICE, "sub": f"g-racer{i}", "email": f"racer{i}@gmail.com"})
    when = night(22)
    forms = []
    for i, c in enumerate(clients):
        forms.append({"name": "Racer", "phone": "01712345678", "payer_number": "01712345678",
                      "trx_id": f"RACE{i:06d}", "no_refund": "1", "date": when[0], "slot": when[1],
                      "csrf_token": token(c, f"/book?date={when[0]}&slot={when[1]}")})
    codes = []
    threads = [threading.Thread(target=lambda c=c, f=f: codes.append(c.post("/book", data=f).status_code))
               for c, f in zip(clients, forms)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [302] + [409] * 5  # the database lets exactly one in


# --- 3. the owner confirms, rejects, cancels; the customer is emailed ---------------------------

def test_owner_confirms_and_the_customer_is_emailed(site):
    app, fake = site
    alice, owner = app.test_client(), app.test_client()
    sign_in(alice, fake, ALICE)
    book(alice, night(19), "TRXALICE01")

    assert "Invalid username or password" in owner_login(owner, "wrong").get_data(as_text=True)
    assert owner_login(owner).status_code == 302
    dash = page_text(owner, "/admin/")
    assert "Payments to check" in dash and "TRXALICE01" in dash and "01712345678" in dash

    row = booking_row(app, "TRXALICE01")
    done = admin_post(owner, f"/admin/bookings/{row.id}/confirm")
    assert f"Confirmed {row.booking_code}" in done and f"Email sent to {ALICE['email']}" in done

    subject, body = fake.last(ALICE["email"])
    assert "confirmed" in subject and row.booking_code in subject
    assert "TRXALICE01" in body and "৳500" in body and "Pay at the ground: ৳1,500" in body
    assert "Arrive 10 minutes early" in body
    assert booking_row(app, "TRXALICE01").email_sent_at is not None
    assert state_of(alice, night(19)) == "booked"

    again = admin_post(owner, f"/admin/bookings/{row.id}/confirm")
    assert "Cannot confirm a CONFIRMED booking" in again
    assert len([m for m in fake.sent if m["To"] == ALICE["email"]]) == 1  # no second email


def test_owner_rejects_with_a_reason_and_the_slot_frees(site):
    app, fake = site
    alice, bob, owner = app.test_client(), app.test_client(), app.test_client()
    sign_in(alice, fake, ALICE)
    sign_in(bob, fake, BOB)
    book(alice, night(19), "TRXALICE01")
    owner_login(owner)
    row = booking_row(app, "TRXALICE01")
    for path in ("/admin/", "/admin/bookings"):  # the owner can type the reason next to Reject
        assert 'name="note"' in page_text(owner, path) and "Reason (optional" in page_text(owner, path)

    page = admin_post(owner, f"/admin/bookings/{row.id}/reject", note="No payment with this TrxID")
    assert f"{row.booking_code} rejected" in page and "The slot is free again" in page
    subject, body = fake.last(ALICE["email"])
    assert "not going ahead" in subject and "Reason: No payment with this TrxID" in body
    assert state_of(bob, night(19)) == "available"

    assert book(bob, night(19), "TRXBOB0001").status_code == 302  # someone else can book it now
    assert book(alice, night(20), "TRXALICE01").status_code == 400  # a used TrxID stays used


def test_owner_cancels_a_confirmed_booking(site):
    app, fake = site
    alice, owner = app.test_client(), app.test_client()
    sign_in(alice, fake, ALICE)
    book(alice, night(19), "TRXALICE01")
    owner_login(owner)
    row = booking_row(app, "TRXALICE01")
    admin_post(owner, f"/admin/bookings/{row.id}/confirm")
    assert 'aria-label="Cancel ' in page_text(owner, "/admin/bookings")

    page = admin_post(owner, f"/admin/bookings/{row.id}/reject")
    assert f"{row.booking_code} cancelled" in page and "The slot is free again" in page
    subject, body = fake.last(ALICE["email"])
    assert "not going ahead" in subject and "Reason: Cancelled by the ground" in body
    assert booking_row(app, "TRXALICE01").status == Booking.REJECTED
    assert state_of(alice, night(19)) == "available"


def test_a_failed_email_never_undoes_the_owners_action_and_can_be_resent(site):
    app, fake = site
    alice, owner = app.test_client(), app.test_client()
    sign_in(alice, fake, ALICE)
    book(alice, night(19), "TRXALICE01")
    owner_login(owner)
    row = booking_row(app, "TRXALICE01")

    fake.gmail_down = True
    page = admin_post(owner, f"/admin/bookings/{row.id}/confirm")
    assert "Confirmed, but the email couldn't be sent" in page
    assert booking_row(app, "TRXALICE01").status == Booking.CONFIRMED
    assert booking_row(app, "TRXALICE01").email_sent_at is None
    assert "Resend email" in page_text(owner, "/admin/bookings")

    fake.gmail_down = False
    resent = admin_post(owner, f"/admin/bookings/{row.id}/email")
    assert f"Email sent to {ALICE['email']}" in resent
    assert booking_row(app, "TRXALICE01").email_sent_at is not None
    assert "Resend email" not in page_text(owner, "/admin/bookings")


def test_without_email_set_up_the_owner_is_told_so(site):
    app, fake = site
    app.config["GMAIL_REFRESH_TOKEN"] = ""  # production before the Gmail setup (Appendix D17)
    alice, owner = app.test_client(), app.test_client()
    sign_in(alice, fake, ALICE)
    book(alice, night(19), "TRXALICE01")
    owner_login(owner)
    row = booking_row(app, "TRXALICE01")
    page = admin_post(owner, f"/admin/bookings/{row.id}/confirm")
    assert f"Confirmed {row.booking_code}" in page and "Email isn't set up yet" in page
    assert booking_row(app, "TRXALICE01").status == Booking.CONFIRMED and fake.sent == []
    assert "Email sending" in page_text(owner, "/admin/")  # on the setup checklist


# --- 4. blocks, closing online booking, the admin's own safety ---------------------------------

def test_blocking_a_slot_and_closing_online_booking(site):
    app, fake = site
    alice, owner = app.test_client(), app.test_client()
    sign_in(alice, fake, ALICE)
    owner_login(owner)
    date, slot = night(21)

    blocked = owner.post("/admin/slots/block", data={"csrf_token": token(owner, "/admin/calendar"),
                                                    "date": date, "slot": slot, "reason": "Maintenance"},
                         follow_redirects=True)
    assert "Blocked" in blocked.get_data(as_text=True)
    assert state_of(alice, night(21)) == "blocked"
    assert book(alice, night(21), "TRXALICE01").status_code == 409

    with app.app_context():
        block = db.session.scalar(db.select(Booking).where(Booking.status == Booking.BLOCKED))
    owner.post(f"/admin/slots/{block.id}/unblock", data={"csrf_token": token(owner, "/admin/calendar")})
    assert state_of(alice, night(21)) == "available"

    with app.app_context():
        db.session.get(TurfSettings, 1).bkash_number = ""
        db.session.commit()
    assert "isn't open yet" in alice.get(f"/book?date={date}&slot={slot}").get_data(as_text=True)
    assert book(alice, night(21), "TRXALICE01").status_code == 400
    assert "bKash merchant number" in page_text(owner, "/admin/")  # on the setup checklist


def test_admin_pages_need_the_owner_and_wrong_passwords_lock_out(site):
    app, fake = site
    stranger = app.test_client()
    for path in ("/admin/", "/admin/bookings", "/admin/calendar", "/admin/settings"):
        response = stranger.get(path)
        assert response.status_code == 302 and "/admin/login" in response.location
    with app.app_context():
        anyone = Booking(booking_code="TZ-AAAAAA", customer_name="X", phone="01712345678",
                         booking_date=current_operating_day() + timedelta(days=2), slot_time=dt.time(19),
                         status=Booking.PENDING, trx_id="TRXPRIVATE1")
        db.session.add(anyone)
        db.session.commit()
        booking_id = anyone.id
    # a stranger can't confirm without a CSRF token, nor with one but no sign-in
    assert stranger.post(f"/admin/bookings/{booking_id}/confirm").status_code == 400
    response = stranger.post(f"/admin/bookings/{booking_id}/confirm",
                             data={"csrf_token": token(stranger, "/admin/login")})
    assert response.status_code == 302 and "/admin/login" in response.location
    assert booking_row(app, "TRXPRIVATE1").status == Booking.PENDING

    for _ in range(5):
        owner_login(stranger, "wrong")
    assert owner_login(stranger).status_code == 429  # locked out even with the right password

    # the owner's own way back in: "Forgot username or password?" emails a one-use link
    owner = app.test_client()
    owner.environ_base["REMOTE_ADDR"] = "10.0.0.9"  # another connection: the lockout is per address
    owner.post("/admin/forgot", data={"csrf_token": token(owner, "/admin/forgot"), "email": "tturfzone@gmail.com"})
    subject, body = fake.last("tturfzone@gmail.com")
    link = re.search(r"http://localhost(/admin/reset/\S+)", body).group(1)
    new_password = "a brand new long password"
    owner.post(link, data={"csrf_token": token(owner, link), "new_password": new_password,
                      "confirm_password": new_password})
    assert owner_login(owner, OWNER_PASSWORD).status_code == 200  # the old password no longer works
    assert owner_login(owner, new_password).status_code == 302


# --- 5. the whole pipeline in one unbroken run ------------------------------------------------

def test_full_pipeline_from_sign_in_to_sign_out(site):
    """One customer, start to finish: sign in with Google, book and pay, the owner confirms
    (email), the owner cancels with a reason (email), the slot is free again, sign out."""
    app, fake = site
    player, owner = app.test_client(), app.test_client()
    when = night(20)

    # 1. the customer lands on the homepage and opens booking: signed out, so offered a sign-in
    assert player.get("/").status_code == 200
    gate = player.get(f"/book?date={when[0]}&slot={when[1]}")
    assert gate.status_code == 200 and "/login?next=" in gate.get_data(as_text=True)

    # 2. signs in with Google and comes back to the booking page with the same slot
    back = sign_in(player, fake, ALICE, next_path=f"/book?date={when[0]}%26slot={when[1]}")
    assert back.status_code == 302
    form = page_text(player, f"/book?date={when[0]}&slot={when[1]}")
    assert ALICE["email"] in form and BKASH in form and "৳500" in form and "Sign out" in form

    # 3. pays ৳500 by bKash and submits the TrxID: the slot is held, payment being checked
    sent = book(player, when, "PIPE0TRX01")
    assert sent.status_code == 302 and sent.location.endswith("/book/success")
    assert "Payment being checked" in page_text(player, "/book/success")
    assert state_of(player, when) == "pending"
    row = booking_row(app, "PIPE0TRX01")
    assert row.status == Booking.PENDING and row.customer_email == ALICE["email"]

    # 4. the owner signs in, sees it under Payments to check, confirms: customer emailed
    assert owner_login(owner).status_code == 302
    assert "PIPE0TRX01" in page_text(owner, "/admin/")
    confirmed = admin_post(owner, f"/admin/bookings/{row.id}/confirm", back="/admin/")
    assert f"Confirmed {row.booking_code}" in confirmed and f"Email sent to {ALICE['email']}" in confirmed
    subject, body = fake.last(ALICE["email"])
    assert subject == f"Your TTURFZONE booking is confirmed ({row.booking_code})"
    assert "PIPE0TRX01" in body and "Advance paid: ৳500" in body and "Pay at the ground: ৳1,500" in body
    assert state_of(player, when) == "booked"

    # 5. the owner cancels it with a reason: customer emailed again, slot free for others
    cancelled = admin_post(owner, f"/admin/bookings/{row.id}/reject", note="Floodlight repairs that night")
    assert f"{row.booking_code} cancelled" in cancelled
    subject, body = fake.last(ALICE["email"])
    assert subject == f"Your TTURFZONE booking {row.booking_code} is not going ahead"
    assert "Reason: Floodlight repairs that night" in body
    assert state_of(player, when) == "available"
    assert [m["Subject"] for m in fake.sent if m["To"] == ALICE["email"]] == [
        f"Your TTURFZONE booking is confirmed ({row.booking_code})",
        f"Your TTURFZONE booking {row.booking_code} is not going ahead"]  # exactly two, in order
    assert all(m["From"] == "TTURFZONE <tturfzone@gmail.com>" for m in fake.sent)

    # 6. both sign out
    assert owner.post("/admin/logout", data={"csrf_token": token(owner, "/admin/")}).status_code == 302
    assert owner.get("/admin/").status_code == 302
    assert player.post("/auth/logout", data={"csrf_token": token(player, "/")}).status_code == 302
    assert ALICE["email"] not in page_text(player, "/book")


# --- 6. a guest books without Google (CR-13) --------------------------------------------------

def test_guest_booking_without_google_no_email(site):
    """No sign-in: the booking holds the slot, the owner confirms and cancels, nobody is emailed,
    and the owner is told to call or WhatsApp instead."""
    app, fake = site
    guest, owner = app.test_client(), app.test_client()
    when = night(21)

    sent = book(guest, when, "GUEST0TRX1", phone="01911222333")
    assert sent.status_code == 302 and sent.location.endswith("/book/success")
    done = page_text(guest, "/book/success")
    assert "Payment being checked" in done and "01911222333" in done
    assert state_of(guest, when) == "pending"
    row = booking_row(app, "GUEST0TRX1")
    assert row.status == Booking.PENDING and row.customer_email is None

    assert owner_login(owner).status_code == 302
    dashboard = page_text(owner, "/admin/")
    assert "GUEST0TRX1" in dashboard and "No email" in dashboard
    confirmed = admin_post(owner, f"/admin/bookings/{row.id}/confirm", back="/admin/")
    assert f"Confirmed {row.booking_code}" in confirmed and "No email on this booking" in confirmed
    assert state_of(guest, when) == "booked"
    assert "Resend email" not in page_text(owner, "/admin/bookings")

    cancelled = admin_post(owner, f"/admin/bookings/{row.id}/reject", note="Rain")
    assert f"{row.booking_code} cancelled" in cancelled and "No email on this booking" in cancelled
    assert state_of(guest, when) == "available"
    assert fake.sent == []  # nobody was emailed

    # the same TrxID can't book a second slot, guest or not
    again = book(guest, night(22), "GUEST0TRX1")
    assert again.status_code == 400
