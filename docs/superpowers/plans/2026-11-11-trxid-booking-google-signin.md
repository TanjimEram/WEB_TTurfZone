# TrxID Booking + Google Sign-in + Gmail Email (Part B, CR-9) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A customer signs in with Google, pays the ৳500 advance by bKash *Payment* to the merchant number, submits the TrxID and the number paid from; the booking holds its slot as PENDING until the owner confirms or rejects it, and the customer gets an email from tturfzone@gmail.com either way.

**Architecture:** Google sign-in and the Gmail API are plain HTTPS calls through one small stdlib helper (`services/google.py`), faked in tests. Bookings gain three nullable columns (email, payer number, unique TrxID); `turf_settings` gains the bKash number and advance amount. `PENDING` (already in the database slot rule, D-42) is the "payment being checked" state, so the double-booking rule is untouched. Emails are sent after the status change is committed and never undo it.

**Tech Stack:** Flask, Flask-SQLAlchemy, Flask-Migrate, Jinja, stdlib `urllib`/`http.server`, pytest; MariaDB 11.4 production.

**Spec:** `docs/superpowers/specs/2026-11-11-trxid-booking-24-slots-redesign-design.md` (Part B)

## Global Constraints

- No new dependency: Google OAuth, the token exchange and the Gmail API go through stdlib `urllib.request` (D-08 unchanged).
- Secrets only in env: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`; `MAIL_FROM` = `TTURFZONE <tturfzone@gmail.com>`. Never log tokens, codes or response bodies that contain them. Unit tests never call Google; they patch `services.google._post_form` / `_get_json` / `_post_json`.
- Redirect URIs are built from `SITE_URL`, never the request Host: `SITE_URL + /auth/google/callback`; the Gmail authorisation uses `http://localhost:8765/gmail-callback` (registered 2026-11-11).
- Booking is only possible signed in (CR-9 reverses D-35). The email on a booking always comes from the Google session, never from the form.
- TrxID: trimmed, upper-cased, 8–12 letters/digits; unique across all bookings (database unique index `uq_bookings_trx_id`). Payer number normalised like `phone`.
- A new booking is `PENDING` and holds its slot until the owner acts (no auto-release). `PAYMENTS_ENABLED=false` now means this flow; `true` still raises `NotImplementedError`.
- Email after commit; a failed email never undoes confirm/reject; the owner sees it and can resend (CLAUDE.md notification rule).
- Advance default ৳500 (C-22); no refund on cancellation, shown before submit and required as a checkbox.
- All Dhaka-time rules unchanged (D-52). Commits `<type>(M4.9|M5.11): ...`; plan + CLAUDE.md updated in the final task; `pytest -q` and `pytest -q -m mariadb` green before push.

## Review Focus

1. A customer starts on `https://www.tturfzone.com`: the OAuth `state` lives in a cookie for `www`, but Google returns to `tturfzone.com`. Expected: `/auth/google` first redirects to the `SITE_URL` host, so the round trip works. (Task 2 `test_google_start_moves_to_site_url_host`.)
2. The same TrxID submitted twice at the same moment by two people: exactly one booking; the other gets "already used", not a 500. (Task 1 `test_duplicate_trx_id_is_refused`, Task 1 MariaDB `test_trx_id_unique_on_mariadb`.)
3. Gmail refuses or the token was revoked while the owner confirms: the booking is still CONFIRMED, the owner sees the email failure and a Resend button. (Task 4 `test_confirm_survives_email_failure_and_offers_resend`.)
4. Someone posts to `/book` with an `email` field to book under another address: ignored; the session's Google email is stored. (Task 3 `test_email_comes_from_google_session_not_form`.)
5. Google returns `email_verified: false` or the user presses Cancel on Google's page: no session, a clear message on the sign-in page. (Task 2 `test_unverified_google_email_is_refused`, `test_google_cancel_shows_message`.)

---

### Task 1: Booking and settings data (M4.9)

**Files:**
- Create: `database/migrations/versions/d5e1a7c3b9f2_trxid_booking.py`
- Modify: `models/booking.py`, `models/turf_settings.py`, `services/bookings.py`
- Test: `tests/test_bookings.py`, `tests/test_mariadb.py`

**Interfaces:**
- Produces:
  - `Booking.customer_email` String(254), `Booking.payer_number` String(14), `Booking.trx_id` String(20) unique (index `uq_bookings_trx_id`), `Booking.email_sent_at` DateTime UTC (used by Task 4); all nullable.
  - `TurfSettings.bkash_number` String(20) nullable, `TurfSettings.advance_bdt` Integer nullable (NULL means 500, `ADVANCE_DEFAULT_BDT = 500` in `services/bookings.py`).
  - `create_booking_request(name, phone, booking_date, slot_time, *, email: str, payer_number: str, trx_id: str) -> Booking` inserting `PENDING`. Errors in `BookingValidationError.errors` keys `name`, `phone`, `payer_number`, `trx_id`, `slot`. Duplicate TrxID → `errors["trx_id"] = "This transaction ID has already been used."` (pre-check query plus the unique index as the race backstop).
  - `normalize_trx_id(raw) -> str` (raises `BookingValidationError({"trx_id": "Enter the bKash transaction ID (TrxID) from your payment message."})`).
- Migration: add the 4 booking columns + `uq_bookings_trx_id`, the 2 settings columns; downgrade removes them. Hand-check it doesn't touch `uq_active_slot` / `active_slot_key`.

- [ ] **Step 1: Tests** in `tests/test_bookings.py` (replace the "confirmed immediately" test):

```python
def test_new_booking_is_pending_with_payment_details(app): ...
    # create_booking_request(..., email="a@b.test", payer_number="+8801812345678", trx_id=" 8n7a6d5e4f ")
    # -> status PENDING, customer_email "a@b.test", payer_number "01812345678", trx_id "8N7A6D5E4F"
def test_pending_booking_holds_the_slot(app): ...            # second request same slot -> SlotUnavailableError
def test_bad_trx_id_and_payer_number_are_reported_together(app): ...  # "12", "abc" -> errors trx_id + payer_number
def test_duplicate_trx_id_is_refused(app): ...                 # same TrxID, other slot -> errors["trx_id"] "already been used"
def test_duplicate_trx_id_race_is_a_validation_error(app, monkeypatch): ...
    # pre-check patched to see nothing; the unique index rejects -> BookingValidationError, not IntegrityError
```

`tests/test_mariadb.py`: tables test unchanged (no new table); add `test_trx_id_unique_on_mariadb` (two rows with the same TrxID → second raises; two rows with NULL TrxID → fine).

- [ ] **Step 2: Run** `pytest -q tests/test_bookings.py` — Expected: FAIL (unexpected keyword `email`).
- [ ] **Step 3: Implement** model columns, migration, `normalize_trx_id`, new `create_booking_request`. `_is_trx_conflict(exc)`: `"trx_id" in str(exc.orig)` (covers `uq_bookings_trx_id` on MariaDB/PostgreSQL and `bookings.trx_id` on SQLite).
- [ ] **Step 4: Run** `pytest -q tests/test_bookings.py` — PASS; other suites may fail on the old signature until Task 3.
- [ ] **Step 5: Commit** `feat(M4.9): bookings carry email, bKash payer number and a unique TrxID; new bookings are PENDING`.

### Task 2: Google sign-in (M4.9)

**Files:**
- Create: `services/google.py`, `routes/auth.py`, `templates/login.html`, `templates/privacy.html`
- Modify: `config.py` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` from env; testing: fake values), `app.py` (register `auth` blueprint), `templates/partials/nav.html` (Login / "name · Sign out"), `routes/public.py` (`/privacy`)
- Test: `tests/test_google_signin.py`

**Interfaces:**
- `services/google.py`:
  - `_post_form(url, data: dict) -> dict`, `_get_json(url, token: str) -> dict`, `_post_json(url, token: str, payload: dict) -> dict` — the only network calls; raise `GoogleError` on any HTTP/network/JSON failure, never including bodies in the message.
  - `sign_in_url(state: str) -> str` (scopes `openid email profile`, `prompt=select_account`, redirect `SITE_URL/auth/google/callback`).
  - `user_from_code(code: str) -> dict` → `{"sub", "email", "name"}`; raises `GoogleError("not verified")` when `email_verified` is false.
- `routes/auth.py` blueprint `auth`:
  - `GET /login?next=` page with "Continue with Google" (says sign-in isn't set up when `GOOGLE_CLIENT_ID` is empty).
  - `GET /auth/google?next=` — if `request.host` ≠ host of `SITE_URL`, redirect to the same path on `SITE_URL`; else store `oauth_state` (secrets.token_urlsafe(24)) + safe `oauth_next` (starts with `/`, not `//`) and redirect to `sign_in_url`.
  - `GET /auth/google/callback` — `state` must equal the popped session state (`hmac.compare_digest`); `error=access_denied` → back to `/login` with "Google sign-in was cancelled."; `GoogleError` → "Couldn't sign in with Google. Please try again."; success → `session["customer"] = {"sub", "email", "name"}` → redirect `oauth_next` or `/book`.
  - `POST /auth/logout` (CSRF) — removes `customer` only.
  - Also in `routes/auth.py`: `current_customer() -> dict | None` and the decorator `customer_login_required` (redirects to `/login?next=<full path>`).
- `/privacy`: what is collected (Google name + email, phone, bKash number paid from, TrxID), why (bookings and their emails only), not shared or sold, contact tturfzone@gmail.com. No other claims.

- [ ] **Step 1: Tests** (`tests/test_google_signin.py`, Google faked by monkeypatching `services.google._post_form` and `_get_json`):

```python
def test_google_start_redirects_with_state_and_fixed_redirect_uri(client): ...
def test_google_start_moves_to_site_url_host(client, app): ...      # Host www.example -> 302 to SITE_URL host, same path
def test_callback_signs_in_and_returns_to_next(client): ...         # session customer email set, Location == next
def test_callback_with_wrong_state_is_refused(client): ...          # no customer in session
def test_unverified_google_email_is_refused(client): ...
def test_google_cancel_shows_message(client): ...                   # ?error=access_denied -> /login with message
def test_google_network_failure_shows_message(client): ...          # fake raises GoogleError
def test_offsite_next_is_ignored(client): ...                       # next=https://evil -> /book
def test_logout_keeps_nothing(client): ...
def test_login_page_without_client_id_says_not_set_up(client, app): ...
def test_privacy_page_lists_what_is_collected(client): ...
def test_tokens_never_logged(client, caplog): ...                    # fake token "SECRET-TOKEN" absent from caplog.text
```

- [ ] **Step 2: Run** `pytest -q tests/test_google_signin.py` — FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(M4.9): Google sign-in (stdlib OAuth), privacy page`.

### Task 3: Booking page with bKash payment (M4.9)

**Files:**
- Modify: `routes/public.py` (`book`, `book_submit`, `booking_success`), `templates/booking.html`, `templates/booking_success.html`, `services/settings.py` + `routes/admin.py` + `templates/admin/settings.html` (bKash number + advance fields), `templates/partials/footer.html` and homepage copy that says "confirmed instantly / no online payment"
- Test: `tests/test_public_routes.py`, `tests/test_admin_routes.py`, `tests/test_production_content.py`

**Interfaces:**
- `GET /book` and `POST /book` are `customer_login_required`.
- Booking form fields: `name` (prefilled from the Google name), `phone`, `payer_number`, `trx_id`, `no_refund` (checkbox, required: `errors["no_refund"] = "Please confirm you understand the advance isn't refunded."`), hidden `date`/`slot`. Shows the signed-in email (not a field). Payment box: "Open bKash → **Payment** → merchant number **{bkash_number}** → amount **৳{advance}** → then enter the TrxID below."
- No `bkash_number` set → the form is replaced by "Online booking isn't open yet." plus WhatsApp/phone if set; `POST /book` returns 400 with the same message.
- Success page: "Payment being checked", booking code, date, time, TrxID, "We'll email {email} when it's confirmed.", WhatsApp link if set.
- Settings: `bkash_number` (normalised like phones, optional), `advance_bdt` (1–100000, default shown 500).
- Copy that says "confirmed instantly" / "no online payment" → "Pay a ৳{advance} bKash advance; the rest at the ground. We confirm by email."

- [ ] **Step 1: Tests:**

```python
def test_book_requires_google_sign_in(client): ...                 # GET/POST /book -> /login?next=...
def test_signed_in_booking_is_pending_with_session_email(client, app): ...
def test_email_comes_from_google_session_not_form(client, app): ...
def test_no_refund_box_required(client, app): ...
def test_booking_closed_without_bkash_number(client, app): ...
def test_success_page_says_payment_being_checked(client, app): ...
def test_settings_save_bkash_number_and_advance(as_admin, app): ...
```

A `signed_in` fixture sets `session["customer"]` with `client.session_transaction()`. Update existing booking tests to sign in and send the new fields.

- [ ] **Step 2: Run** the three files — FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — PASS. Browser check at 375 px only if `.env` has the Google client keys (real sign-in on localhost); otherwise tests only, and say so.
- [ ] **Step 5: Commit** `feat(M4.9): booking needs sign-in and a bKash TrxID; payment being checked`.

### Task 4: Owner confirmation emails via the Gmail API (M5.11)

**Files:**
- Modify: `services/google.py` (Gmail send + token refresh), `services/mailer.py` (Gmail transport when `GMAIL_REFRESH_TOKEN` is set), `cli.py` (`gmail-authorize`), `routes/admin.py` (confirm/reject send email; `POST /admin/bookings/<id>/email`), `templates/admin/dashboard.html` ("Payments to check"), `templates/admin/bookings.html` + `calendar.html` (TrxID, payer number, email)
- Create: `services/booking_emails.py`
- Test: `tests/test_booking_emails.py`, `tests/test_admin_routes.py`, `tests/test_cli.py`, `tests/test_admin_recovery.py` (mailer still captured)

**Interfaces:**
- `services/google.py`: `gmail_access_token() -> str` (refresh-token grant, cached in a module dict until 60 s before expiry); `gmail_send(raw_message: bytes) -> None` (POST `users/me/messages/send` with `{"raw": base64url}`); `gmail_consent_url(state) -> str` (scope `https://www.googleapis.com/auth/gmail.send`, `access_type=offline`, `prompt=consent`, redirect `http://localhost:8765/gmail-callback`); `refresh_token_from_code(code) -> str`.
- `services/mailer.py`: `mail_configured()` true when `GMAIL_REFRESH_TOKEN` + `MAIL_FROM` set, or the SMTP settings; `send_email(to, subject, body)` unchanged signature, Gmail first.
- `services/booking_emails.py`: `booking_email(booking, settings) -> (subject, body)` for CONFIRMED ("Your TTURFZONE booking is confirmed": code, real date, time range, advance paid, balance due at the ground = period price − advance when known, rules, contact) and REJECTED ("We couldn't confirm your TTURFZONE booking": code, slot, "we couldn't find your payment", contact); `send_booking_email(booking) -> bool` (never raises; logs the exception type only).
- Admin confirm/reject: after the status commit call `send_booking_email`; flash "Confirmed. Email sent to …" or "Confirmed, but the email couldn't be sent." Rows whose last email failed show **Resend email** (`POST /admin/bookings/<id>/email`, CONFIRMED/REJECTED only). Track with `bookings.email_sent_at` (from Task 1; set on success, cleared when the status changes).
- Dashboard: "Payments to check" table first: every upcoming PENDING row with slot (real date), name, phone, payer number, TrxID, advance, Confirm / Reject.
- `flask gmail-authorize`: prints the consent URL, opens it (`webbrowser.open`), serves one request on `localhost:8765` (stdlib `http.server`), checks `state`, prints the refresh token once with "Put this in cPanel as GMAIL_REFRESH_TOKEN. It is not saved anywhere."

- [ ] **Step 1: Tests:**

```python
def test_confirm_sends_confirmation_email(as_admin, app, outbox): ...
def test_reject_sends_rejection_email_and_frees_slot(as_admin, app, outbox): ...
def test_confirm_survives_email_failure_and_offers_resend(as_admin, app, monkeypatch): ...
def test_resend_email_sends_again_and_hides_button(as_admin, app, outbox): ...
def test_dashboard_lists_payments_to_check_first(as_admin, app): ...
def test_confirmation_email_has_code_date_time_and_balance(app): ...
def test_gmail_send_refreshes_and_caches_token(app, monkeypatch): ...      # 2 sends -> 1 token call
def test_gmail_send_failure_raises_without_secrets(app, monkeypatch): ...
def test_mailer_prefers_gmail_when_refresh_token_set(app, monkeypatch): ...
def test_gmail_authorize_prints_refresh_token(monkeypatch): ...            # fake server + exchange
```

- [ ] **Step 2: Run** the files — FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** — PASS.
- [ ] **Step 5: Commit** `feat(M5.11): owner confirms or rejects payments; customer emailed via the Gmail API`.

### Task 5: Whole suite, MariaDB, docs

- [ ] **Step 1:** `pytest -q` — all pass except 4 PostgreSQL skips. Local MariaDB: `pytest -q -m mariadb` — all pass.
- [ ] **Step 2:** Recompute D16 fingerprints at the new head (bookings and turf_settings change).
- [ ] **Step 3: Docs.**
  - `CLAUDE.md`: "What this project is" (TrxID + owner confirmation now, gateway later); Hard rules — replace "Guest booking must never be blocked behind login" with the CR-9 rule (Google sign-in required; email from the session); add "a TrxID can only be used once (database unique index)"; Commands — `flask --app app gmail-authorize`; env names.
  - `.env.example`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `MAIL_FROM` example.
  - `docs/PROJECT_PLAN.md`: §2 payment/statuses/customer-accounts lines (CR-9), D-35 superseded, new D-54 (TrxID flow, PENDING hold, email after commit, Gmail API transport, stdlib OAuth, host redirect), M4.9 + M5.11 ticked, §4 Google Cloud row, §5.2 new columns, §5.4 routes, §5.5 env, QA items, Appendix D: D17 rewritten for the Gmail API (gmail-authorize on the PC, 4 env vars in cPanel), D16 hashes, Known issues (wrongly rejected TrxID can't be reused; customers without a Google account can't book online), session log, Resume here.
- [ ] **Step 4: Commit** `docs(M5.11): CR-9 recorded; Gmail API runbook` and push.
