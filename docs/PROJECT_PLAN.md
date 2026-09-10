# TTURFZONE project plan (living document)

> For Claude: this file is the project's memory across sessions and accounts. Read "Resume here" first. Update it in the same commit as the work (rules in CLAUDE.md). Never write passwords, API keys or connection strings in this file.

## Resume here

| Field | Value |
|---|---|
| Phase | M3 homepage complete. **CR-1 recorded** (self-sufficient: online payments, auto-confirm, SMS/email, holds, cron jobs). Scaffold done locally; waiting on hosting money for real deploy |
| Last completed | Docs: CR-1 written into CLAUDE.md + this plan (documentation only, no code). Before that: M3.1/M3.2/M3.3 homepage, 51 passed, 4 skipped (2026-09-11) |
| Next task | Build continues on the frontend, unaffected by CR-1: M4.1 `/api/availability` tests → M4.2 `static/js/booking.js` slot grid → M2.2, M2.3, then CR-1 M2.6/M2.7 → M4.3–M4.5. See "Execution order (CR-1)" at the end of §6. **Wait for developer go-ahead.** |
| Blocked by | Hosting/domain purchase blocks M1.3b and W3–W6 (postponed). PostgreSQL-only bugs uncaught until W5. **CR-1: M10 blocked by repricing agreement (C-27); M12 blocked by bKash merchant approval (C-21).** |
| Dev environment | Windows + PowerShell. venv: `.venv\Scripts\Activate.ps1`. |
| Live URL | not deployed |
| Repo | created by developer (private GitHub) |

Status keys: `[ ]` to do, `[x]` done, `~~struck through~~ (CR-n)` dropped by a change request.

---

## 1. Snapshot

- Client: TTURFZONE turf ground owner. Facebook: https://www.facebook.com/TTURFZONE
- Found online (confirm with owner): listed on Book My Turf BD as "T Turf Zone", 6-a-side futsal, Notin Rani ghat, New Jailkhana, inside Tripti Sporting Club.
- Reference site, inspiration only, do not copy: https://turfxsonagazi.com
- Brief: `docs/brief/TTURFZONE_Claude_Code_Project_Brief.pdf`
- Budget: originally ৳10,000 / 2 days. **CR-1 reprices to ~Tk 25,000 / 4–5 days (not yet agreed with client).** Built with Claude Code.
- Definition of done (brief §19, manual mode / `PAYMENTS_ENABLED=false`): on a phone, a customer selects a date, selects an available 90-minute slot, submits name and phone, and sees a booking ID with PENDING status. The owner logs in securely, sees the request, confirms or rejects it, and blocks slots. Production runs on HTTPS with the production database connected, and duplicate-booking conflicts have been tested.
- Definition of done (CR-1, `PAYMENTS_ENABLED=true`, after merchant approval): the customer pays online, the server verifies the payment with bKash, the booking auto-confirms, and SMS + email go to the customer and the owner. One real small payment and refund tested on production (M12).

## 2. Global constraints (from the brief; change only through a CR)

- Payment (CR-1, overrides brief §2): online bookings are paid up front through the bKash direct gateway, verified server-to-server, then auto-confirmed. Config flag `PAYMENTS_ENABLED` toggles this. When `false` (launch state, until merchant approval) a booking is a `PENDING` request the owner confirms or rejects — the original brief §2 behaviour. No payment data is ever trusted from a redirect or query string.
- Statuses: PENDING (awaiting owner, manual mode), PENDING_PAYMENT (hold while the customer pays, CR-1), CONFIRMED (accepted/paid, unavailable to others), REJECTED (declined by owner, slot free again), EXPIRED (payment hold ran out, CR-1), CANCELLED (cancelled after confirmation, CR-1), BLOCKED (owner prevents booking).
- Fixed 90-minute slots: 06:00, 07:30, 09:00, 10:30, 12:00, 13:30, 15:00, 16:30, 18:00, 19:30, 21:00, 22:30.
- Duplicate bookings are prevented on the server/database side. Client-side availability is never trusted. The `uq_active_slot` partial unique index covers PENDING_PAYMENT, PENDING, CONFIRMED and BLOCKED (CR-1).
- Mobile-first. Persistent mobile actions: WHATSAPP and BOOK NOW.
- Never invent business information. Use `TODO(owner):` placeholders for missing data.
- Reviews: only genuine, owner-approved. Facebook: link only, no Facebook API.
- WhatsApp: deep link only, no paid messaging API. WhatsApp Business API stays in the Backlog (CR-1).
- Notifications (CR-1): SMS via a Bangladeshi SMS API and email via the hosting SMTP mailbox. Written to an outbox table and sent by a scheduled job with retries. A failed SMS or email never fails or rolls back a booking.
- Scheduled jobs (CR-1): cPanel cron once a minute runs Flask CLI commands to expire holds, send queued notifications and send reminders.
- Secrets only in environment variables. Passwords hashed. Admin routes protected. HTTPS in production. Customer booking data never public.
- Readable, beginner-friendly code. Separate config, models, routes, services and templates. No unnecessary dependencies.
- Excluded (updated by CR-1): customer accounts, automated WhatsApp API, multiple branches, tournaments, coupons/loyalty, complex analytics, native app, AI chatbot, large CMS. (`online payments/bKash` and `SMS gateway` were removed from this list by CR-1 and are now in scope.)
- Visual direction (unless the owner's brand says otherwise): dark base, energetic green accent, white typography, high-contrast CTAs, large real photos, clean cards, restrained motion.

## 3. Decisions

| ID | Decision | Why | Status |
|---|---|---|---|
| D-01 | Flask + Jinja + vanilla JS + PostgreSQL | Brief §8 | Final |
| D-02 | Database: use the hosting plan's own PostgreSQL if it has one with backups; otherwise Neon Free (region nearest the app server). Not Supabase Free. | Supabase Free pauses a project after 7 days without activity and has no downloadable backups. Neon Free scales to zero after 5 idle minutes and wakes automatically in milliseconds. | Proposed, finalize in M0.3 |
| D-03 | App hosting: Bangladeshi cPanel hosting with Python app support (Passenger), paid in BDT, account in the owner's name. Fallback: Render Starter (about $7/month, needs an international card) + Neon. | No cold starts, bKash payment, local support, low yearly cost. Free Render/Koyeb tiers sleep, which is bad for a booking site opened from Facebook. | Proposed, finalize in M0.3 |
| D-04 | Blocks are rows in `bookings` with status BLOCKED (reason in `admin_note`). No separate BlockedSlot table. | One partial unique index then prevents every conflict (booking vs booking, booking vs block). Brief §2 already treats BLOCKED as a booking status; brief §10 allows schema refinement. | Final unless developer objects |
| D-05 | **Manual mode only** (`PAYMENTS_ENABLED=false`): a PENDING request holds its slot until the owner confirms or rejects. Max 2 future PENDING requests per phone number. Under CR-1 payments, holds are `PENDING_PAYMENT` and last `HOLD_MINUTES` (see D-26). | Matches brief §2 (REJECTED frees the slot); the cap limits spam in manual mode. | Manual mode: confirm with owner (C-03). Payment mode: D-26 |
| D-06 | Owner can reject a CONFIRMED booking too (shown as "Cancel") | Real customers cancel; the owner must be able to free the slot | Final |
| D-07 | Plain CSS with custom properties, no Tailwind build step | Nothing to compile on cPanel; fewer moving parts | Final |
| D-08 | Dependencies: Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF, psycopg[binary], python-dotenv, tzdata; dev: pytest. CR-1 adds `requests` (D-33). `itsdangerous` (signed tokens, D-11) and `smtplib`/`email` (SMTP, D-30) ship with Flask / the stdlib. Add gunicorn only if deploying to Render. | Flask-Migrate: future schema changes on live data. Flask-WTF: CSRF protection. tzdata: zoneinfo on Windows has no timezone database. | Final (CR-1 additions) |
| D-09 | Slot times are a constant in `services/slots.py` for the MVP | Settings-driven slot config is future work (Backlog) | Final |
| D-10 | Business logic uses Asia/Dhaka time (`zoneinfo`). Slots stored as local `date` + `time`; audit fields as `timestamptz`. | Server may run in UTC | Final |
| D-11 | Success / payment-result page reads the booking from the session or from a short-lived signed token (`itsdangerous`, already a Flask dependency), not a public `/booking/<code>` URL. The token carries only the booking id and a short expiry. | Brief §13: do not expose customer data publicly. A payment gateway returns the user to a fixed URL, so the session alone is not always enough — a signed, expiring token is safe. | Final (updated by CR-1) |
| D-12 | `/healthz` does not touch the database | Uptime pings must not keep Neon awake and burn free compute hours | Final |
| D-13 | Owner content (about, facilities, reviews, pricing, gallery list, contact, hours) lives in one `turf_settings` row, seeded from `database/seed_data.py` | One place to edit; admin settings page (M7.4) can edit it later | Final |
| D-14 | Admin password generated by `create-admin` (20 random chars, shown once). Login rate limiting moved to Backlog. | Fits the 2-day window; strong generated password lowers brute-force risk | Final |
| D-15 | ৳10,000 is the development fee. Domain and hosting are billed to the owner separately and registered in the owner's name. | Recurring costs belong to the owner; clean handover | **Superseded by CR-1 pending repricing** (developer estimate ~Tk 25,000). Not deleted. |
| D-16 | Budget ranges shown to client: hosting Tk 3,000–4,000 (max 5,000)/yr, .com domain Tk 1,200–1,500 (max 2,000)/yr, DB/SSL/WhatsApp Tk 0. Running cost max Tk 7,000/yr; year-1 total max Tk 17,000. Nothing bought above the max without written approval. | Advance must not be spent on infrastructure | **Superseded by CR-1 pending repricing** — CR-1 adds bKash fees (1.5–2%/txn) and SMS cost (~Tk 0.25–0.40 each) to the owner's running costs. Not deleted. |
| D-18 | Dev-only diagnostics: `/dev/wiring` page and `fake-*` CLI commands, fake rows use `FK-` codes. Registered only when `ENABLE_DEV_TOOLS` (development). | Test DB connection, migrations, conflict rule and API before real features and before hosting exists | Final |
| D-19 | `scripts/serve_like_passenger.py` uses stdlib `wsgiref` to import `passenger_wsgi.application` in production mode | Rehearse cPanel loading without buying hosting; no new dependency | Final |
| D-20 | `requirements-dev.txt` adds pytest on top of `requirements.txt`; production installs only `requirements.txt` | Keep production minimal | Final |
| D-21 | `config.normalize_database_url()` converts `postgres://`/`postgresql://` to `postgresql+psycopg://` | Paste Neon/cPanel URLs unchanged | Final |
| D-22 | Short seed fields (phone, whatsapp: 20 chars) seed as empty strings; the TODO lives in a comment | PostgreSQL rejected long placeholder text (caught by testing on Postgres) | Final |
| D-23 | Admin scope: the owner manages bookings, blocks slots, and edits basic settings (phone, WhatsApp, address, hours, booking rules, prices). Photos, page text, colours and layout are changed by the developer. A content editor (gallery upload, hero photo, about text, reviews, facilities) is a paid phase 2, in the Backlog. | Keeps the 2-day MVP small; media handling and rich text are their own project | Final (developer, 2026-09-11) |
| D-17 | Payments: (1) Tk 5,000 development advance before build; (2) hosting + domain actual cost (up to Tk 7,000) before build, paid by owner directly or sent with receipts; (3) Tk 5,000 balance at handover after owner tests live site. Unused infra money returned or deducted from payment 3. 2-day clock starts after payments 1–2 and Day-1 inputs. 7 days of free fixes after handover. | Protects developer from funding infra out of the advance; protects deadline from late assets | **Superseded by CR-1 pending repricing** — payment schedule and totals reissued in an updated client summary (the .docx is outside the repo; developer handles it). Not deleted. |
| D-24 | `PAYMENTS_ENABLED` config flag (default `false`). `false` = original owner-confirmation flow (PENDING → owner confirms). `true` = online payment holds + auto-confirm. Site launches with it `false` and switches to `true` after bKash merchant approval (M12). | Ship a working site before merchant approval; one switch to go live on payments; both flows always present and tested. | Final (CR-1) |
| D-25 | bKash **direct** payment gateway (tokenized flow: grant token → create payment → execute payment → query payment). All gateway code sits behind one interface in `services/payments/` (`base.py` abstract class + `bkash.py`), so booking logic never imports a gateway directly and a second gateway can be added later. Fallback if bKash direct is not workable: an aggregator such as SSLCommerz (reported setup fee Tk 15,000–25,000 — get a written quote first). | No setup fee, ~1.5–2%/txn, widely used in BD. Interface keeps the coupling to one place. | Proposed (CR-1); confirm once the merchant application starts |
| D-26 | Slot holds: new statuses `PENDING_PAYMENT` (hold while paying), `EXPIRED` (hold ran out), `CANCELLED` (cancelled after confirmation). `uq_active_slot` covers `PENDING_PAYMENT, PENDING, CONFIRMED, BLOCKED`. Holds last `HOLD_MINUTES` (default 10). Booking creation **must expire stale holds for that slot in the same transaction** before inserting; a per-minute cron job (`jobs-expire-holds`) is the backup. New booking fields: `hold_expires_at`, `amount_due_bdt`, `customer_email` (optional), `source` (`online`\|`phone`\|`walk_in`). | An unexpired-looking row still occupies the unique index, so lazy expiry at creation time is required for correctness; cron alone is not enough. | Final (CR-1) |
| D-27 | `payments` table (see §5.2). One row per payment attempt; `merchant_invoice` unique; `raw_response` JSON stores gateway responses **with no secrets/tokens**. | Audit trail; idempotency key; refund records. | Final (CR-1) |
| D-28 | `notifications` outbox table (see §5.2). All SMS/email are queued rows sent by `jobs-send-notifications` with retries (`attempts`, `last_error`, `send_after`). Sending failure never touches the booking transaction. | Decouples slow/unreliable providers from the booking; makes retries and reminders simple. | Final (CR-1) |
| D-29 | Scheduled jobs are Flask CLI commands run by cPanel cron every minute: `jobs-expire-holds`, `jobs-send-notifications`, `jobs-send-reminders`. Not added to CLAUDE.md Commands until they exist. | cPanel has cron; no extra worker process or dependency (no Celery/RQ). | Final (CR-1) |
| D-30 | Email via the hosting account's SMTP mailbox (`MAIL_*` env vars), Python stdlib `smtplib` / `email`. SPF and DKIM DNS records set at deploy (M8). No transactional-email SaaS. | Included with hosting, no extra cost, no new dependency. | Final (CR-1) |
| D-31 | SMS via a Bangladeshi SMS API provider (chosen later). Start with a **non-masking** sender (~Tk 0.25–0.40/SMS); register the branded `TTURFZONE` sender name later (a few working days). | Non-masking works immediately; masking needs registration lead time. | Proposed (CR-1); provider is C-2x |
| D-32 | Deferred to Backlog: WhatsApp Business API, automatic refunds via bKash API, Nagad/card payments via an aggregator. v1 refunds are done in the bKash merchant dashboard and **recorded** in admin (M5.7). | Keeps CR-1 to a shippable size. | Final (CR-1) |
| D-33 | HTTP client dependency: `requests` (for bKash and SMS API calls). Justification: readable, universally known, simple to fake in tests. | One obvious, well-documented client rather than raw `urllib` or an async stack. | Final (CR-1) |

## 4. Infrastructure and accounts (no secrets here)

| Service | Purpose | Account owner | Status | Notes |
|---|---|---|---|---|
| Domain (.com preferred) | Website address | Owner is registrant; developer has access | Not bought | Buy from the chosen host. Record renewal date and renewal price. |
| Hosting (BD cPanel, Python) | Runs Flask app | Owner's email; login shared privately | Not chosen | Must pass Appendix B checks before paying |
| PostgreSQL | Production DB | Owner's email | Not created | Host PostgreSQL or Neon (D-02). Neon: create `production` and `dev` branches. |
| GitHub (private repo) | Code | Developer now; **transferred to the owner's account at handover, developer re-added as collaborator** (M9.7) | Not created | |
| Google Maps | Map embed + directions link | None | n/a | Embed iframe and share link, no API key |
| bKash merchant (CR-1) | Online payments | Owner's name (trade licence, TIN, business bank account, NID) | Not started | Sandbox first; live needs approval ~1–3 weeks. Refunds via the merchant dashboard in v1. |
| SMS API provider (CR-1) | Customer + owner SMS | Owner's name; prepaid balance | Not chosen | Non-masking first; branded `TTURFZONE` sender registered later. Owner tops up balance. |
| Email / SMTP (CR-1) | Customer + owner email | Hosting mailbox (owner's hosting account) | Not created | Set SPF + DKIM DNS records at deploy (M8). |

Credentials are handed to the owner privately (in person or a password manager share), never through this repo.

## 5. Architecture and contracts

### 5.1 File map

```
tturfzone/
├── CLAUDE.md
├── app.py                    # create_app(), registers blueprints, CLI commands, security headers
├── config.py                 # DevConfig, TestConfig, ProdConfig (read from env)
├── extensions.py             # db = SQLAlchemy(), migrate = Migrate(), csrf = CSRFProtect()
├── cli.py                    # db-check, seed-settings, create-admin, fake-*; CR-1: jobs-expire-holds, jobs-send-notifications, jobs-send-reminders
├── passenger_wsgi.py         # cPanel entry: from app import create_app; application = create_app()
├── requirements.txt
├── requirements-dev.txt      # + pytest
├── pytest.ini                # pythonpath, postgres marker
├── .env.example
├── .gitignore                # .env, .venv, __pycache__, instance/, *.sqlite
├── docs/
│   ├── PROJECT_PLAN.md
│   └── brief/TTURFZONE_Claude_Code_Project_Brief.pdf
├── models/
│   ├── __init__.py           # exports Admin, Booking, TurfSettings; CR-1: Payment, Notification
│   ├── _time.py              # utcnow()
│   ├── admin.py
│   ├── booking.py            # CR-1: new statuses + hold_expires_at, amount_due_bdt, customer_email, source
│   ├── turf_settings.py
│   ├── payment.py            # CR-1
│   └── notification.py       # CR-1 (outbox)
├── routes/
│   ├── __init__.py
│   ├── public.py             # blueprint "public": /, /book, /book/success, /healthz
│   ├── dev.py                # blueprint "dev" (development only): /dev/wiring + fake-data buttons
│   ├── api.py                # blueprint "api": /api/availability
│   ├── payments.py           # CR-1 blueprint "payments": /pay/start, /pay/bkash/callback, /pay/result
│   └── admin.py              # blueprint "admin": /admin/... (CR-1: manual booking, payments list, refunds)
├── services/
│   ├── __init__.py
│   ├── slots.py              # slot constants, Dhaka time, bookability, day availability
│   ├── bookings.py           # create/confirm/reject/block/unblock, validation, codes; CR-1: expire holds, PENDING_PAYMENT
│   ├── payments/             # CR-1: base.py (PaymentGateway ABC), bkash.py, __init__.py (get_gateway())
│   ├── notifications.py      # CR-1: queue_*, render templates, send_due() used by the job
│   ├── jobs.py               # CR-1: expire_holds(), send_notifications(), send_reminders()
│   ├── fake_data.py          # FK- fake bookings, double-booking probe (development)
│   └── db_health.py          # check_database() used by db-check and /dev/wiring
│   └── auth.py               # login_required, verify_admin
├── templates/
│   ├── base.html
│   ├── partials/             # nav, footer, sticky_actions, slot_grid, flash
│   ├── index.html
│   ├── booking.html
│   ├── booking_success.html
│   ├── payment_result.html   # CR-1: paid / failed / cancelled / timed-out
│   ├── errors/404.html, errors/500.html
│   └── admin/ base_admin.html, login.html, dashboard.html, bookings.html, calendar.html, settings.html,
│              booking_new.html (CR-1 manual booking), payments.html (CR-1 list + refund record)
├── static/
│   ├── css/ main.css, admin.css
│   ├── js/ booking.js, gallery.js, reveal.js, admin.js
│   ├── images/ hero/, gallery/, og-image.jpg, logo.*
│   └── icons/
├── notification_templates/   # CR-1: plain-text SMS + email bodies (English; Bangla later)
├── scripts/
│   └── serve_like_passenger.py   # cPanel/Passenger simulation
├── database/
│   ├── migrations/           # Flask-Migrate (Migrate(app, db, directory="database/migrations"))
│   └── seed_data.py          # TurfSettings defaults with TODO(owner) placeholders
└── tests/
    ├── conftest.py                 # app (SQLite in-memory), client, pg_url
    ├── test_config.py, test_app_wiring.py, test_passenger_entrypoint.py
    ├── test_booking_rules_db.py, test_fake_data.py, test_availability_api.py
    ├── test_db_health.py, test_cli.py, test_dev_tools.py, test_seed_data.py
    ├── test_postgres.py            # @pytest.mark.postgres: migrations, partial index, 10-thread race
    ├── test_slots.py               # M2.2
    ├── test_bookings.py            # M2.3
    ├── test_holds.py               # CR-1 M2.7: hold expiry inside booking creation (+ @pytest.mark.postgres)
    ├── test_payments.py            # CR-1 M10: gateway interface + fake bKash, verification, idempotency
    ├── test_payment_routes.py      # CR-1 M10: /pay/* with a fake gateway
    ├── test_notifications.py       # CR-1 M11: outbox queue, retries, failure never rolls back a booking
    ├── test_jobs.py                # CR-1 M11: expire_holds / send_notifications / send_reminders
    ├── test_sandbox.py             # CR-1: @pytest.mark.sandbox, real bKash sandbox, skipped without creds
    ├── test_public_routes.py       # M4
    └── test_admin_routes.py        # M5 (+ CR-1 M5.6/M5.7)
```

### 5.2 Data model

**admins**: id (PK), username (unique, not null), password_hash (not null, werkzeug `generate_password_hash`), created_at (timestamptz).

**bookings**: id (PK), booking_code (unique, e.g. `TZ-7K3M9Q`), customer_name (nullable for BLOCKED), phone (nullable for BLOCKED, normalized `01XXXXXXXXX`), booking_date (date), slot_time (time), status (see below), admin_note (text, nullable; block reason or rejection note), created_at, updated_at (timestamptz).
CR-1 adds: `hold_expires_at` (timestamptz, nullable — set for PENDING_PAYMENT), `amount_due_bdt` (int, nullable), `customer_email` (string, nullable, optional), `source` (`online|phone|walk_in`, default `online`).

Status (CR-1): `PENDING` (manual mode), `PENDING_PAYMENT` (hold while paying), `CONFIRMED`, `REJECTED`, `EXPIRED`, `CANCELLED`, `BLOCKED`.

Conflict rule, enforced by the database (CR-1: `PENDING_PAYMENT` added to the active set):

```python
_ACTIVE = "status IN ('PENDING_PAYMENT','PENDING','CONFIRMED','BLOCKED')"
__table_args__ = (
    db.Index(
        "uq_active_slot", "booking_date", "slot_time", unique=True,
        postgresql_where=db.text(_ACTIVE),
        sqlite_where=db.text(_ACTIVE),
    ),
    db.Index("ix_bookings_status_date", "status", "booking_date"),
    db.Index("ix_bookings_hold_expires_at", "hold_expires_at"),   # CR-1: cron sweep
    db.CheckConstraint(
        "status IN ('PENDING_PAYMENT','PENDING','CONFIRMED','REJECTED','EXPIRED','CANCELLED','BLOCKED')",
        name="ck_booking_status",
    ),
)
```

Alembic autogenerate can miss the WHERE clause. Always open the generated migration and check it. A stale `PENDING_PAYMENT` row still occupies `uq_active_slot`, so `create_booking_request` must expire that slot's stale holds in the same transaction before inserting (D-26, M2.7).

**payments** (CR-1): id (PK), booking_id (FK bookings, not null), gateway (string, e.g. `bkash`), merchant_invoice (string, **unique** — our idempotency key), gateway_payment_id (string, **unique**, nullable until "create payment" succeeds), amount_bdt (int), status (`INITIATED|SUCCESS|FAILED|CANCELLED|REFUNDED`), raw_response (JSON, **no secrets/tokens**), created_at, updated_at (timestamptz).

**notifications** (CR-1, outbox): id (PK), booking_id (FK, nullable), channel (`sms|email`), recipient (string), template (string, name under `notification_templates/`), body (text, rendered), status (`QUEUED|SENT|FAILED`), attempts (int, default 0), last_error (text, nullable), send_after (timestamptz — reminders and retry backoff), sent_at (timestamptz, nullable), created_at (timestamptz).

**turf_settings** (single row, id = 1): turf_name, tagline, about_text, phone, whatsapp (digits with country code, e.g. `8801XXXXXXXXX`), address, map_embed_url, map_link, facebook_url, opening_hours_text, booking_rules_text, confirm_time_text, booking_window_days (int, default 14), max_pending_per_phone (int, default 2), pricing (JSON), facilities (JSON), reviews (JSON), gallery (JSON), updated_at.

Pricing JSON shape (final values from C-02):

```json
[{"label": "Morning", "slots": ["06:00", "07:30", "09:00"], "days": "all", "price_bdt": 0}]
```

`days` is `all`, `weekday` or `weekend`. If the owner has one flat price, use a single band with all 12 slots.

CR-1 may add owner-tunable fields to `turf_settings` once the owner answers C-24/C-25/C-26: `deposit_percent` (100 = full payment), `reminder_hours_before` (default 2), `cancellation_refund_text`. `HOLD_MINUTES` stays config (env). Decide field vs config when building M10/M11.

### 5.3 Service contracts

`services/slots.py`
- Built: `SLOT_TIMES`, `SLOT_MINUTES`, `TZ`, `now_dhaka()`, `today_dhaka()`, `slot_label()`, `get_day_availability()` (no past/window rules yet). M2.2 adds the rest.
- `SLOT_TIMES: list[datetime.time]` (the 12 slots), `SLOT_MINUTES = 90`, `TZ = ZoneInfo("Asia/Dhaka")`
- `now_dhaka() -> datetime`
- `slot_label(t: time) -> str` returns `"06:00 AM"` style
- `is_valid_slot(t: time) -> bool`
- `booking_window(today: date, days: int) -> list[date]` (today plus the next `days - 1` days)
- `is_bookable(d: date, t: time, now: datetime | None = None) -> bool` (valid slot, slot start in the future, date inside window)
- `get_day_availability(d: date) -> list[dict]` returns `{"time": "06:00", "label": "06:00 AM", "state": "available|pending|booked|blocked|past", "price_bdt": int | None}`. No customer data. CR-1: a live `PENDING_PAYMENT` hold (not past `hold_expires_at`) reports `state: "pending"`; expired holds report `available`.

`services/bookings.py`
- Built: `SlotUnavailableError`, `generate_booking_code(prefix="TZ") -> str`, `save_booking(booking: Booking) -> Booking` (commits; converts uq_active_slot IntegrityError to SlotUnavailableError). All later functions must save through `save_booking`.
- `class BookingValidationError(Exception)` with `.errors: dict[str, str]`
- `class SlotUnavailableError(Exception)`
- `class InvalidTransitionError(Exception)`
- `normalize_phone(raw: str) -> str` accepts `01XXXXXXXXX`, `+8801...`, `8801...`; regex `^01[3-9]\d{8}$` after normalizing; raises `BookingValidationError`
- `generate_booking_code() -> str` (`TZ-` + 6 chars from `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`, `secrets`)
- `create_booking_request(name, phone, booking_date, slot_time, *, email=None, source="online") -> Booking` validates, checks pending cap (manual mode), **expires this slot's stale holds in the same transaction (CR-1, D-26)**, inserts, catches `IntegrityError` → `SlotUnavailableError`. Manual mode inserts `PENDING`; payment mode inserts `PENDING_PAYMENT` with `hold_expires_at = now + HOLD_MINUTES` and `amount_due_bdt`.
- `confirm_booking(booking_id: int) -> Booking` (from PENDING in manual mode; from PENDING_PAYMENT after verified payment in CR-1). Idempotent: confirming an already-CONFIRMED booking is a no-op, not an error (CR-1).
- `reject_booking(booking_id: int, note: str | None = None) -> Booking` (PENDING or CONFIRMED)
- `cancel_booking(booking_id: int, note: str | None = None) -> Booking` (CR-1: CONFIRMED → CANCELLED; frees the slot; queues a cancellation notice)
- `expire_stale_holds(*, booking_date=None, slot_time=None, now=None) -> int` (CR-1) marks PENDING_PAYMENT rows past `hold_expires_at` as `EXPIRED`; scoped to one slot when args given (used inside `create_booking_request`), unscoped for the cron job. Returns count.
- `block_slot(booking_date: date, slot_time: time, reason: str) -> Booking` raises `SlotUnavailableError` if taken
- `unblock_slot(booking_id: int) -> None` deletes the BLOCKED row
- `dashboard_summary(today: date) -> dict` with keys `today`, `pending_count`, `upcoming`

`services/payments/` (CR-1)
- `base.py`: `class PaymentGateway(ABC)` — `create_payment(booking, amount_bdt) -> Payment`, `execute_payment(payment) -> Payment`, `query_payment(payment) -> Payment`, `refund(payment, amount_bdt, reason) -> Payment` (may raise `NotImplementedError` in v1). Exceptions: `PaymentError`, `PaymentDeclined`, `PaymentVerificationError`.
- `bkash.py`: `class BkashGateway(PaymentGateway)` — tokenized flow (grant/refresh token cached in memory, create, execute, query). Verifies amount and `merchant_invoice` on query before returning SUCCESS. Never logs tokens or raw auth headers.
- `__init__.py`: `get_gateway(name: str | None = None) -> PaymentGateway` from `PAYMENT_GATEWAY` config. Tests inject `FakeGateway`.

`services/notifications.py` (CR-1)
- `queue(channel, recipient, template, context, *, booking_id=None, send_after=None) -> Notification` renders the template body and inserts a `QUEUED` row. Never sends inline.
- `queue_booking_confirmed(booking)`, `queue_owner_alert(booking)`, `queue_reminder(booking)`, `queue_cancelled(booking)` — helpers that queue the right rows (customer SMS + email if present; owner SMS + email to `OWNER_ALERT_*`).
- `send_due(now=None, limit=50) -> dict` picks `QUEUED`/retry-due rows, sends via the SMS client or SMTP, updates `status`/`attempts`/`last_error`/`sent_at`. Catches all provider errors per row; a failure is recorded, never raised.

`services/jobs.py` (CR-1) — thin wrappers the CLI calls
- `expire_holds(now=None) -> int` → `bookings.expire_stale_holds()`
- `send_notifications(now=None) -> dict` → `notifications.send_due()`
- `send_reminders(now=None) -> int` queues reminder rows for CONFIRMED bookings whose slot is `reminder_hours_before` away and have no reminder queued yet (idempotent).

`services/auth.py`
- `verify_admin(username: str, password: str) -> Admin | None`
- `login_required` decorator; session key `admin_id`; `session.clear()` on login and logout

### 5.4 Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Homepage with all sections and quick booking grid |
| GET | `/book?date=&slot=` | Booking page, preselects date/slot |
| POST | `/book` | Create request (CSRF), redirect to success or re-render with errors |
| GET | `/book/success` | One-time confirmation from session or signed token (D-11) |
| GET | `/api/availability?date=YYYY-MM-DD` | Public slot states (JSON) |
| GET | `/healthz` | Returns `ok`, no DB |
| POST | `/pay/start` | CR-1: create a PENDING_PAYMENT booking + `payments` row, call gateway "create payment", redirect to the gateway |
| GET, POST | `/pay/bkash/callback` | CR-1: gateway return. Server-side "execute" + "query", verify amount + `merchant_invoice`, confirm booking, queue notifications. **Idempotent.** Then redirect to `/pay/result` |
| GET | `/pay/result?t=<signed token>` | CR-1: paid / failed / cancelled / timed-out page (no customer data in the URL) |
| GET, POST | `/admin/login` | Owner login |
| POST | `/admin/logout` | Logout |
| GET | `/admin/` | Dashboard |
| GET | `/admin/bookings?date=&status=` | Filterable list |
| POST | `/admin/bookings/<id>/confirm` | Confirm |
| POST | `/admin/bookings/<id>/reject` | Reject or cancel |
| GET | `/admin/calendar?date=` | 12-slot day view with actions |
| POST | `/admin/slots/block` | Block (date, slot_time, reason) |
| POST | `/admin/slots/<id>/unblock` | Unblock |
| GET, POST | `/admin/bookings/new` | CR-1 (M5.6): manual booking for `phone` / `walk_in` customers |
| POST | `/admin/bookings/<id>/cancel` | CR-1: cancel a CONFIRMED booking |
| GET | `/admin/payments?status=&date=` | CR-1 (M5.7): payments list |
| POST | `/admin/payments/<id>/refund` | CR-1 (M5.7): record a refund done in the bKash dashboard (note + amount) |
| GET, POST | `/admin/settings` | Basic settings (M7.4) |

WhatsApp link after booking: `https://wa.me/<whatsapp>?text=` + URL-encoded `"Hi, I requested a booking at TTURFZONE. Booking ID: TZ-XXXXXX, Date: ..., Time: ..."`.

### 5.5 Environment variables (`.env.example` lists names only)

`APP_ENV` (development|testing|production), `SECRET_KEY`, `DATABASE_URL` (`postgresql+psycopg://...`, add `?sslmode=require` for Neon), `TEST_DATABASE_URL` (optional, for the postgres test).

CR-1 (names only; values only in the environment, never in git or .md):
`PAYMENTS_ENABLED` (default false), `PAYMENT_GATEWAY` (e.g. `bkash`), `HOLD_MINUTES` (default 10),
`BKASH_BASE_URL`, `BKASH_APP_KEY`, `BKASH_APP_SECRET`, `BKASH_USERNAME`, `BKASH_PASSWORD`,
`SMS_API_URL`, `SMS_API_KEY`, `SMS_SENDER_ID`,
`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`,
`OWNER_ALERT_PHONE`, `OWNER_ALERT_EMAIL`.
Sandbox tests read `BKASH_*` from the environment and skip when unset (`@pytest.mark.sandbox`).

Engine options: `pool_pre_ping=True`, `pool_recycle=280` (Neon closes idle connections when it scales to zero).

Production config: `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"`, `PERMANENT_SESSION_LIFETIME=12h`. Response headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.

---

## 6. Milestones and tasks

Times are targets. If a milestone runs over by more than an hour, tell the developer and propose what to cut (log it as a CR).

### M0 Pre-build (Day 0)

- [ ] M0.1 Send client message (Appendix A). Collect C-01 to C-11 answers.
- [ ] M0.2 Get client sign-off on `TTURFZONE_Project_Summary_and_Budget.docx` (D-15 to D-17). Receive Tk 5,000 advance and hosting/domain payment (up to Tk 7,000).
- [ ] M0.3 Shortlist 2 Bangladeshi Python hosting plans. Ask Appendix B questions through their live chat. Pick one; finalize D-02 and D-03.
- [ ] M0.4 Buy hosting + domain in the owner's name (owner pays). Enable AutoSSL. Do this before Day 1 starts: DNS and SSL can take hours.
- [ ] M0.5 If Neon: create project (region nearest the host server) with `production` and `dev` branches.
- [x] M0.6 Create private GitHub repo. Commit CLAUDE.md, docs/PROJECT_PLAN.md, brief PDF.
- [ ] M0.7 Local setup: Python version matching the host (3.10+), Git, editor, Claude Code.

Done when: repo exists with docs, hosting and DB are accessible, C-01 to C-07 answered.

### M1 Scaffold and walking-skeleton deploy (Day 1, 09:00 to 10:30)

- [x] M1.1 `requirements.txt`, `.gitignore`, `.env.example`, `config.py`, `extensions.py`, `app.py` (factory, blueprints, headers), `cli.py` with `db-check`, `templates/base.html`, `/healthz`.
- [x] M1.2 `tests/conftest.py` (app with TestConfig, SQLite in-memory, CSRF off in tests), one test for `/healthz`.
- [x] M1.3a `passenger_wsgi.py` + `scripts/serve_like_passenger.py`; production-mode simulation verified (healthz ok, /dev 404, headers set, refuses to start without SECRET_KEY/DATABASE_URL).
- [ ] M1.3b Deploy skeleton to the real host: Setup Python App, env vars, `pip install -r requirements.txt`, `flask db upgrade`, `flask db-check` from the host terminal. Blocked until hosting is bought.
- [x] M1.4 Dev wiring page `/dev/wiring`, `services/db_health.py`, `services/fake_data.py`, fake CLI commands (D-18).

Done when: `pytest -q` passes; host URL (temporary URL is fine) returns `ok` at `/healthz`; `db-check` succeeds on the host. This proves the risky parts early.

### Wiring check (developer, local, before hosting exists)

- [ ] W1 Unzip scaffold into repo, `pip install -r requirements-dev.txt`, `pytest -q` shows 42 passed, 4 skipped.
- [ ] W2 SQLite: copy `.env.example` to `.env`, set SECRET_KEY, `flask db upgrade`, `seed-settings`, `run --debug`, open `/dev/wiring`, press all three buttons.
- [x] W1 done (2026-09-11): `pytest -q` shows 42 passed, 4 skipped on Windows.
- [x] W2 done (2026-09-11): local SQLite, `/dev/wiring` works, all three buttons pressed.
- [ ] W3 POSTPONED until hosting/DB is bought. Neon: create project (region nearest Bangladesh, Singapore), branches `dev` and `test`. Put `dev` URL in `DATABASE_URL`, `test` URL in `TEST_DATABASE_URL`.
- [ ] W4 POSTPONED. Neon: `flask db-check` (expect missing tables), `flask db upgrade`, `db-check` shows Database OK, `seed-settings`, `fake-bookings`, `fake-conflict-test`, `/dev/wiring` shows postgresql.
- [ ] W5 POSTPONED. `pytest -q -m postgres` against Neon `test` branch: 4 passed. Until this runs, PostgreSQL-only problems are not caught (see Risks).
- [ ] W6 POSTPONED. `serve_like_passenger.py` in production mode against Neon `dev`: `/healthz` ok, `/dev/wiring` 404.

### M2 Data model and booking rules (Day 1, 10:30 to 12:30)

- [x] M2.1 Models (5.2), Flask-Migrate at `database/migrations`, first migration, verify partial index WHERE clause.
- [ ] M2.2 `services/slots.py` + `tests/test_slots.py`: 12 valid slots, past slot today not bookable, outside window not bookable, Dhaka time used (freeze `now`).
- [ ] M2.3 `services/bookings.py` + `tests/test_bookings.py`: valid create, name/phone validation, phone normalization, same slot twice raises `SlotUnavailableError`, reject frees slot, block prevents booking, pending cap per phone, confirm only from PENDING.
- [x] M2.4 Concurrency test (built early as `tests/test_postgres.py`; 10 threads, exactly 1 wins; passed on PostgreSQL 16). Re-run on Neon dev/test branch. Was: `tests/test_bookings_concurrency.py` (`@pytest.mark.postgres`): 10 threads book the same slot; exactly 1 succeeds. Run against Neon `dev` branch or local Postgres.
- [x] M2.5 `cli.py`: `create-admin`, `seed-settings` using `database/seed_data.py` (placeholders only).
- [ ] M2.6 (CR-1) New booking statuses (`PENDING_PAYMENT`, `EXPIRED`, `CANCELLED`) + fields (`hold_expires_at`, `amount_due_bdt`, `customer_email`, `source`); migration — check `uq_active_slot` WHERE clause covers `PENDING_PAYMENT` and the `ck_booking_status` list. `Payment` and `Notification` models + migration.
- [ ] M2.7 (CR-1) `expire_stale_holds()` + hold expiry **inside** `create_booking_request` (same transaction). Tests in `tests/test_holds.py`: a stale hold does not block a new booking; a live hold does; `EXPIRED` frees the slot; concurrency — two customers race an expired-hold slot, exactly one wins (`@pytest.mark.postgres`).

Done when: all tests pass, including the postgres marker.

### M3 Homepage (Day 1, 12:30 to 14:30)

- [x] M3.1 `static/css/main.css`: design tokens (colour, type scale ~1.2, 4px spacing), buttons (primary/ghost/whatsapp, 44px touch, hover/press), cards + `.card--interactive`, `.ph` placeholder blocks (no stock images), header/nav, hero with scrim, slot grid states, footer, sticky mobile actions, `.wa-fab`, `.reveal` hooks, `prefers-reduced-motion` block. System fonts only. `base.html`: skip link, meta description, `{% block scripts %}`. Dev `/dev/wiring` styles ported. (2026-09-11)
- [x] M3.2 `index.html` sections: hero, quick-booking placeholder grid (12 slot labels, static until M4.2), about, facilities, pricing, gallery (6 labelled placeholders), location (map embed placeholder + Get directions), reviews, Facebook, footer. All content via `TurfSettings.current_or_default()` (new: returns a transient TODO-placeholder row when unseeded). Partials: `partials/_macros.html` (photo/owner_text/camera), `partials/footer.html`. Every gap renders a visible `TODO(owner)` note naming its C-nn row. `tests/test_home_page.py` (7 tests): every section renders, no customer name/phone on `/` or `/api/availability`. 49 passed, 4 skipped. (2026-09-11)
- [x] M3.3 `partials/nav.html` (brand, desktop links >=900px, hamburger + full-screen menu below), `partials/sticky_actions.html` (WHATSAPP + BOOK NOW, hidden >=900px) + desktop WhatsApp FAB (only when a number is set), `static/js/main.js` (header `.at-top` over hero then solid; menu open/close/Esc/link-close, body scroll lock, focus return). Smooth scroll + header offset via CSS (`scroll-behavior`, `scroll-padding-top`), reduced-motion honoured. `tests/test_home_page.py` +2. 51 passed, 4 skipped. (2026-09-11) M3 complete.

Done when: layout works at 360px, 768px and 1280px, and every `TODO(owner)` maps to a Client inputs row.

### M4 Booking flow (Day 1, 14:30 to 18:00)

- [ ] M4.1 `routes/api.py` `/api/availability` + tests (bad date → 400; response has no names or phones).
- [ ] M4.2 `static/js/booking.js`: date chips for the booking window, fetch availability, distinct slot states, disabled slots not selectable, loading skeleton, retry on error, animated selection.
- [ ] M4.3 Details and review step; POST `/book` with CSRF; server re-validates; slot-taken error refreshes the grid with a clear message.
- [ ] M4.4 `booking_success.html`: BOOKING REQUEST RECEIVED, booking ID, date, time, name, PENDING owner confirmation, `confirm_time_text`, CHAT ON WHATSAPP button.
- [ ] M4.5 `tests/test_public_routes.py`: happy path, invalid phone, taken slot, past slot, success page without session redirects home.

Done when: the whole flow takes under a minute on a phone-sized viewport, and a duplicate attempt shows a friendly error.

### M5 Admin (Day 1, 18:00 to 22:00)

- [ ] M5.1 Login/logout, `login_required`, session hardening, generic "invalid username or password".
- [ ] M5.2 Dashboard: today's bookings, pending count, next 7 days.
- [ ] M5.3 Bookings list with date and status filters; confirm / reject / cancel buttons (POST + CSRF); tap-to-call and WhatsApp links per customer.
- [ ] M5.4 Calendar: pick a date, see 12 slots with state and actions; block with reason; unblock.
- [ ] M5.5 `tests/test_admin_routes.py`: every admin route redirects when logged out; confirm, reject, block, unblock work.
- [ ] M5.6 (CR-1) `/admin/bookings/new`: manual booking for `phone` / `walk_in` customers (name, phone, optional email, date, slot; `source` set; no payment; goes straight to CONFIRMED or PENDING per owner choice). Uses `create_booking_request` so hold expiry + the unique index still apply.
- [ ] M5.7 (CR-1) `/admin/payments` list (filter by status/date) and `/admin/payments/<id>/refund` to record a refund done in the bKash dashboard (amount + note; sets `payments.status = REFUNDED`; optionally cancels the booking). No refund API call in v1.

Done when: the owner flow works end to end at phone width.

### M6 Day 1 wrap (22:00 to 23:30)

- [ ] M6.1 Run QA checklist sections A to C locally; fix critical bugs only.
- [ ] M6.2 Push and deploy the current build to the host.
- [ ] M6.3 Update this plan; list missing client inputs for a morning follow-up message.

### M7 Content and polish (Day 2, 09:00 to 14:00)

- [ ] M7.1 Real assets: logo, photos converted to WebP (hero about 1600px wide, gallery about 800px, thumbnails about 400px), `loading="lazy"`, text, prices, reviews, map.
- [ ] M7.2 `gallery.js` lightbox (keyboard, swipe, close on Esc); `reveal.js` scroll reveal with IntersectionObserver that respects `prefers-reduced-motion`; success animation.
- [ ] M7.3 SEO and sharing: title, meta description, Open Graph tags and `og-image.jpg` (Facebook link previews), favicon, LocalBusiness JSON-LD using confirmed info only.
- [ ] M7.4 `/admin/settings` for phone, WhatsApp, address, hours, booking rules, prices. If behind schedule, drop to Backlog via CR and keep `seed-settings`.
- [ ] M7.5 404/500 pages; accessibility pass (labels, contrast, focus, alt text).

Done when: Lighthouse mobile targets reached or noted (performance 85+, accessibility 90+; targets, not blockers).

### M8 Production deploy (Day 2, 14:00 to 17:00)

- [ ] M8.1 Production env vars on the host: `APP_ENV=production`, new random 64-char `SECRET_KEY`, production `DATABASE_URL`.
- [ ] M8.2 `flask db upgrade`, `seed-settings`, `create-admin` on production. No test data left.
- [ ] M8.3 Force HTTPS (cPanel setting or `.htaccess`), confirm certificate on the root domain and www, secure cookies active.
- [ ] M8.4 Backups: confirm the host/Neon backup policy; take a manual `pg_dump` before handover; write restore steps in Known issues or handover notes.
- [ ] M8.5 (CR-1) cPanel cron: three entries, once a minute — `flask jobs-expire-holds`, `flask jobs-send-notifications`, `flask jobs-send-reminders`. Confirm they run and log.
- [ ] M8.6 (CR-1) Email: create the SMTP mailbox; set SPF and DKIM DNS records; send one test email and check it is not spam-filed.
- [ ] M8.7 (CR-1) Set the new environment variables (§5.5). Launch with `PAYMENTS_ENABLED=false`. bKash + SMS creds stay as sandbox/empty until M12.

Done when: `https://<domain>` loads, http redirects to https, admin login works on production, cron entries run, a test email arrives.

### M9 QA and handover (Day 2, 17:00 to 21:00)

- [ ] M9.1 Full QA checklist on a real Android phone, an iPhone if available, and desktop.
- [ ] M9.2 Production duplicate-booking test: two phones submit the same slot at the same moment; one succeeds. Delete test rows.
- [ ] M9.3 Owner training: 10-minute screen recording in Bangla (log in, confirm, reject, cancel, block, settings).
- [ ] M9.4 Handover pack delivered privately: accounts list, credentials, renewal dates and prices, how to request changes, support terms.
- [ ] M9.5 Set the Facebook page action button to the website booking page; add the site to Google Business Profile if one exists.
- [ ] M9.6 Tag `v1.0.0`; final plan update.
- [ ] M9.7 Transfer the GitHub repo to the owner's account and re-add the developer as a collaborator.
- [ ] M9.8 (CR-1) Owner training covers: manual booking (phone/walk-in), recording a refund, reading the payments list, topping up SMS balance. Handover pack (M9.4) lists the bKash, SMS and email accounts.

### M10 Payments — sandbox (CR-1)

Blocked from starting by: repricing + owner running-cost agreement (CR-1).

- [ ] M10.1 `services/payments/base.py` `PaymentGateway` ABC + exceptions; `get_gateway()`; `FakeGateway` for tests.
- [ ] M10.2 `services/payments/bkash.py`: token grant/refresh (cached), create / execute / query. Verifies amount + `merchant_invoice`. No token or auth header ever logged.
- [ ] M10.3 `POST /pay/start`: create PENDING_PAYMENT booking (hold) + `payments` row (`merchant_invoice`), call create-payment, redirect to gateway.
- [ ] M10.4 `/pay/bkash/callback`: server-side execute + query, verify, `confirm_booking`, `notifications.queue_booking_confirmed` + `queue_owner_alert`. **Idempotent** — a second callback for the same `merchant_invoice` returns the same result, no double confirm/notify.
- [ ] M10.5 `/pay/result` with signed token (D-11); `templates/payment_result.html` for paid / failed / user-cancelled / timed-out (hold expired).
- [ ] M10.6 Failure paths: declined, user cancel, gateway timeout, callback never arrives (hold expires and frees the slot).
- [ ] M10.7 Tests: `tests/test_payments.py`, `tests/test_payment_routes.py` with `FakeGateway` (success, decline, tampered amount, duplicate callback, wrong `merchant_invoice`). `tests/test_sandbox.py` `@pytest.mark.sandbox` against the real bKash sandbox, skipped without creds.

Done when: with `PAYMENTS_ENABLED=true` and `FakeGateway`, the full pay → verify → CONFIRMED → notifications-queued flow passes, and every failure path frees the slot or lets the hold expire.

### M11 Notifications and scheduled jobs (CR-1)

- [ ] M11.1 `services/notifications.py`: `queue`, the four `queue_*` helpers, `send_due`. Templates in `notification_templates/` (English; Bangla later) — customer confirmation, owner alert, reminder, cancellation.
- [ ] M11.2 SMS client (uses `requests`, `SMS_API_*`); fake in tests. Non-masking sender first.
- [ ] M11.3 Email via `smtplib` + `MAIL_*`; fake in tests.
- [ ] M11.4 `services/jobs.py` + `cli.py` commands `jobs-expire-holds`, `jobs-send-notifications`, `jobs-send-reminders`. Add to CLAUDE.md Commands **now that they exist**.
- [ ] M11.5 Reminders: `send_reminders` queues one reminder per CONFIRMED booking `reminder_hours_before` the slot; never a second one.
- [ ] M11.6 Retries + backoff via `attempts` / `send_after` / `last_error`. Cap attempts; leave `FAILED` for the owner to see.
- [ ] M11.7 Tests: `tests/test_notifications.py`, `tests/test_jobs.py` — outbox queue, a provider error marks the row `FAILED` and **never** rolls back or fails the booking, reminder sent exactly once, job commands are idempotent.

Done when: booking confirmation, owner alert, reminder and cancellation are queued and sent by the jobs; a provider outage never breaks a booking.

### M12 Live payments (CR-1)

Blocked by: approved bKash merchant account in the owner's name (C-21).

- [ ] M12.1 Put live `BKASH_*` and `SMS_API_*` credentials in the production environment.
- [ ] M12.2 One real small payment end to end on production; confirm booking auto-confirms and SMS + email arrive.
- [ ] M12.3 One real refund in the bKash dashboard; record it in `/admin/payments`.
- [ ] M12.4 Set `PAYMENTS_ENABLED=true`. Watch the first day (payments list, notification `FAILED` rows, cron logs).
- [ ] M12.5 Register the branded `TTURFZONE` SMS sender; switch `SMS_SENDER_ID` when approved.

Done when: a real customer can pay and get an auto-confirmed booking with notifications, and one real refund has been recorded.

### Execution order (CR-1)

M3 → M4.2 → M2.2, M2.3, M2.6, M2.7 → M4.3–M4.5 → M5 (incl. M5.6, M5.7) → M10 → M11 → M6 / M7 → M8 → M9 → M12.

## 7. QA checklist

**A. Public site (phone first)**
- [ ] Hero, BOOK NOW and WhatsApp visible without scrolling on a 360px screen
- [ ] Sticky mobile bar stays visible and doesn't cover form buttons
- [ ] All sections show real or clearly marked placeholder content; no invented claims
- [ ] Map loads; GET DIRECTIONS opens Google Maps
- [ ] Gallery lightbox opens, swipes, closes
- [ ] Facebook and WhatsApp links open the right page/number

**B. Booking rules**
- [ ] Past slots today show as unavailable
- [ ] Dates outside the booking window can't be chosen, and the API rejects them
- [ ] Invalid phone numbers rejected with a clear message
- [ ] Booking a PENDING, CONFIRMED or BLOCKED slot fails on the server
- [ ] Rejected or cancelled slot becomes available again
- [ ] Pending cap per phone works
- [ ] Success page shows booking ID and PENDING; refresh doesn't create a second booking

**C. Admin**
- [ ] Every `/admin` page redirects to login when logged out
- [ ] Wrong password shows a generic error
- [ ] Confirm, reject, cancel, block and unblock update the public grid immediately
- [ ] Filters by date and status work
- [ ] Usable at phone width
- [ ] (CR-1) Manual booking for phone / walk-in works and respects the unique index
- [ ] (CR-1) Payments list shows attempts; recording a refund sets REFUNDED and (optionally) frees the slot

**C2. Payments and notifications (CR-1, `PAYMENTS_ENABLED=true`)**
- [ ] Successful payment → booking auto-CONFIRMED, slot taken, customer + owner notified
- [ ] Declined / failed payment → booking not confirmed, slot freed or hold left to expire
- [ ] User cancels at the gateway → same as failed, clear message on the result page
- [ ] Hold times out (no callback) → slot becomes available again; result page says so
- [ ] Duplicate gateway callback → no double confirm, no double notification
- [ ] Tampered amount / wrong `merchant_invoice` → payment rejected, booking not confirmed
- [ ] SMS provider down → booking still CONFIRMED; notification row is `FAILED`/retried, never blocks the booking
- [ ] Reminder is sent once per booking, `reminder_hours_before` the slot
- [ ] With `PAYMENTS_ENABLED=false` the site runs the manual PENDING → owner-confirm flow unchanged
- [ ] No secret, token or auth header appears in logs or `payments.raw_response`

**D. Security**
- [ ] No secrets in the repo (`git grep -i "password\|secret\|postgres://\|app_key\|api_key"` shows only names/placeholders)
- [ ] CSRF token required on all POST forms in production config
- [ ] `/api/availability` contains no customer data
- [ ] Session cookie has Secure, HttpOnly, SameSite in production
- [ ] (CR-1) A booking is only marked paid after a server-to-server gateway query that matches amount + `merchant_invoice`; redirect/query params are never trusted
- [ ] (CR-1) Payment callback is idempotent
- [ ] (CR-1) Gateway / SMS / SMTP credentials only in env; unit tests use fakes; sandbox tests skip without creds

**E. Production**
- [ ] HTTPS on root and www; http redirects
- [ ] Production DB connected; migrations applied
- [ ] Duplicate-booking test done on production (M9.2)
- [ ] 404 page shows for unknown URLs; no debug tracebacks

## 8. Handover checklist

- [ ] Owner can log in to the admin on their own phone
- [ ] Owner has domain and hosting logins (in owner's name) and knows renewal dates
- [ ] GitHub repo transferred to the owner; developer re-added as collaborator (M9.7)
- [ ] Training video delivered
- [ ] Owner knows what the site does not do yet (WhatsApp is a deep link only, no automatic WhatsApp; refunds are manual in the bKash dashboard)
- [ ] (CR-1) bKash merchant, SMS provider and email/SMTP accounts are in the owner's name; logins handed over privately
- [ ] (CR-1) Owner knows how to top up the SMS balance and roughly the per-SMS cost
- [ ] (CR-1) Owner knows how to process a refund in the bKash dashboard and record it in `/admin/payments`
- [ ] (CR-1) Owner knows the `PAYMENTS_ENABLED` switch exists and what "manual mode" means
- [ ] Support and maintenance terms agreed in writing (what's free, what's a paid change)

## 9. Client inputs

Needed by: D0 = before Day 1 starts, D1-AM = Day 1 09:00, D1-PM = Day 1 18:00.

| ID | Item | Needed by | Status | Notes |
|---|---|---|---|---|
| C-01 | Confirm the 12 slot times match opening hours (06:00 to 24:00) | D1-AM | Pending | |
| C-02 | Prices: per slot; any day/night, weekday/weekend or holiday difference | D1-AM | Pending | Fills `pricing` JSON |
| C-03 | Does a pending request hold the slot? OK with max 2 pending per phone? | D1-AM | Pending | D-05 |
| C-04 | How many days ahead customers can book (default 14) | D1-AM | Pending | |
| C-05 | Booking and cancellation rules text | D1-AM | Pending | |
| C-06 | Phone number for calls; WhatsApp number for bookings | D1-AM | Pending | |
| C-07 | Exact address and Google Maps pin link | D1-AM | Pending | |
| C-08 | Domain name choice; registrant full name, email, phone, address | D0 | Pending | |
| C-09 | ৳10,000 = development fee only? Owner pays domain/hosting yearly? | D0 | Pending | D-15 |
| C-10 | Owner email and preferred admin username; anyone else managing bookings? | D1-AM | Pending | MVP has one admin login |
| C-11 | How quickly the owner usually confirms requests | D1-AM | Pending | Shown on success page |
| C-12 | Logo, highest resolution (SVG/PNG) | D1-PM | Pending | |
| C-13 | 10 to 15 original photos from phone/camera: day, night under lights, wide field, facilities | D1-PM | Pending | Not Facebook downloads (compressed) |
| C-14 | Optional 10 to 20 second video | D1-PM | Pending | |
| C-15 | Opening hours and days | D1-AM | Pending | |
| C-16 | Facilities that actually exist | D1-PM | Pending | |
| C-17 | Owner-approved description, 2 to 4 sentences | D1-PM | Pending | |
| C-18 | Real reviews and permission to show names | D1-PM | Pending | |
| C-19 | Confirm Facebook URL; other social links | D1-PM | Pending | |
| C-20 | Sports offered and turf format/size | D1-PM | Pending | Listing says 6-a-side futsal |
| C-21 | bKash merchant documents: trade licence, TIN, business bank account, NID | Before M12 | Pending | CR-1. Blocks live payments (M12). Sandbox build (M10) does not need these |
| C-22 | Full payment up front, or an advance percentage? | Before M10 | Pending | CR-1. Fills `deposit_percent` (100 = full) |
| C-23 | Cancellation and refund rules text (who can cancel, when, how much back) | Before M10 | Pending | CR-1. Shown on the site and used for refund decisions |
| C-24 | Hold length in minutes (default 10) and reminder timing (default 2 hours before) | Before M10 | Pending | CR-1. `HOLD_MINUTES`, `reminder_hours_before` |
| C-25 | Owner alert phone (SMS) and owner alert email | Before M11 | Pending | CR-1. `OWNER_ALERT_PHONE`, `OWNER_ALERT_EMAIL` |
| C-26 | SMS provider preference / budget (or let developer choose) | Before M11 | Pending | CR-1. Non-masking first |
| C-27 | Written agreement to the new development price and the new owner running costs (bKash fees, SMS) | Before M10 start | Pending | CR-1. Blocks M10. Reissued client summary handled by the developer (.docx outside the repo) |

## 10. Change requests

| ID | Date | Request | Type (add/remove/modify) | Impact (time, scope, price) | Affected tasks | Status |
|---|---|---|---|---|---|---|
| CR-1 | 2026-09-11 | Make the website self-sufficient: online payment (bKash direct gateway, server-verified), automatic confirmation, SMS + email notifications, slot holds, scheduled jobs, admin manual bookings + payments/refunds. Overrides brief §2 ("no online payment"); removes "online payments/bKash" and "SMS gateway" from brief §15 exclusions. Still excluded: customer accounts, automated WhatsApp API, multiple branches, tournaments, coupons, complex analytics, native app, AI chatbot, large CMS. | add / modify | **Time:** +2–3 dev days (4–5 total). **Price:** development must be repriced — developer estimate ~Tk 25,000 at the original daily rate, **not yet agreed with the client**; D-15…D-17 superseded pending repricing. **Owner costs:** new running costs (bKash 1.5–2% per txn, SMS ~Tk 0.25–0.40 each, possible masking-sender registration). **Blockers:** live payments need an approved bKash merchant account in the owner's name (trade licence, TIN, business bank account, NID, live URL; ~1–3 weeks). | Global constraints §2; D-05, D-11, D-15–D-17; §5 (models, services, routes, env); new M2.6, M2.7, M5.6, M5.7, M10, M11, M12; M8; §7, §8, §9, §11, §12 | Recorded 2026-09-11. Repricing + owner running-cost agreement pending (blocks M10 start). Merchant approval pending (blocks M12). Frontend (M3, M4.2) continues unaffected. |

## 11. Backlog (after MVP)

- ~~Online payment (bKash/Nagad/SSLCommerz) with advance deposit~~ — now in scope (CR-1)
- ~~Automatic confirmations (SMS or WhatsApp Business API)~~ — SMS/email now in scope (CR-1); WhatsApp API stays below
- WhatsApp Business API for confirmations and reminders (CR-1: deferred)
- Automatic refunds via the bKash refund API (CR-1: v1 records manual refunds only)
- Nagad and card payments via an aggregator (SSLCommerz / aamarPay) (CR-1)
- SMS low-balance alert to the owner (CR-1)
- Bangla notification templates (CR-1: English first)
- Auto-expire manual PENDING requests after X hours (manual mode only; CR-1 already expires PENDING_PAYMENT holds)
- Customer self-cancel with a code
- Login rate limiting and lockout
- Admin content editor (paid phase 2, D-23): gallery upload, hero photo, about text, reviews, facilities editing behind the admin login
- Settings-driven slot templates (different durations, special days)
- Bangla / English language toggle
- Recurring team bookings, tournaments, coupons
- Analytics dashboard
- Multiple turfs or branches
- Scheduled `pg_dump` backup (e.g. GitHub Actions) and uptime monitor that hits `/healthz`

## 12. Risks and open questions

| Risk | Mitigation |
|---|---|
| Client assets arrive late | Placeholders marked `TODO(owner)`; hard deadlines in section 9; follow-up message at M6.3 |
| Host can't run the app (old Python, no SSH, blocked outbound DB port) | Appendix B checks before paying; walking-skeleton deploy in M1.3; fallback D-03 |
| DNS/SSL delay | Buy in M0.4 before Day 1; use host's temporary URL until ready |
| Neon free compute hours used up | `/healthz` without DB (D-12); check usage page after one week |
| Fake PENDING requests block slots | Per-phone cap (D-05), owner rejects; auto-expiry in Backlog |
| Owner slow to confirm | Show `confirm_time_text`; WhatsApp button on success page |
| Scope creep during the 2 days | Every change goes through section 10 with time and price impact |
| (CR-1) Owner has no trade licence → no live bKash merchant account | Site launches and runs in manual mode (`PAYMENTS_ENABLED=false`) indefinitely; M12 waits. Tell the owner early. |
| (CR-1) bKash merchant approval is slow (1–3 weeks or more) | All of M10/M11 is built and tested against the sandbox; going live is one credential swap + M12. |
| (CR-1) bKash sandbox behaves differently from live | Keep verification strict (amount + `merchant_invoice` + query), do one real M12.2 payment before switching the flag. |
| (CR-1) SMS provider outage or bad delivery | Outbox + retries; a failure never blocks a booking; owner also gets an email alert; reminder is best-effort. |
| (CR-1) cPanel cron not running | Holds still expire lazily inside `create_booking_request`; only notifications and reminders wait. Check cron logs at M8.5 and on the first live day. |
| (CR-1) SMS balance runs out | Owner is trained to top up (M9.8); low-balance alert is in the Backlog; email still works. |
| (CR-1) Refund disputes / chargebacks | v1 refunds are manual and logged in admin with a note; cancellation/refund rules text (C-23) is shown to customers up front. |
| (CR-1) Repricing not agreed | M10 does not start until C-27 is signed; frontend work (M3, M4.2) continues meanwhile. |
| PostgreSQL-only problems (VARCHAR length limits, partial-index behaviour, timezone/`timestamptz` handling, JSON columns, concurrency) are not caught while all local work runs on SQLite | W5 (`pytest -q -m postgres`) and W3–W6 are postponed until hosting/DB is bought. Keep model, migration and seed changes conservative until then; run `pytest -m postgres` against Neon the moment it exists and before any deploy (M8). SQLite is treated as UX-only, never as proof. |

## 13. Known issues

- Admin login page is a placeholder until M5; `/admin/login` renders static text.
- `price_bdt` in the availability API is `null` until pricing is wired (M4).
- Homepage verified by tests and a 375px browser pass. A visual pass at 768px and 1280px on a real browser is still pending (do at M6.1 / developer).
- WhatsApp buttons (hero, sticky bar) render disabled and the desktop WhatsApp FAB is hidden until the owner gives the number (C-06). `tel:` link in the footer likewise waits on C-06.
- Homepage quick-book grid is a static, non-interactive placeholder (12 slot labels) until M4.2 wires live availability.
- (CR-1) The footer disclaimer and the success page say "a booking is a request, no online payment" — correct for the launch (`PAYMENTS_ENABLED=false`). This copy must become flag-aware in M10 before M12 flips the flag.
- (CR-1) No `payments` / `notifications` tables or new booking statuses yet — M2.6. All payment/notification tasks (M10–M12) are unstarted and gated (see CR-1 and Risks).

## 14. Session log

| Date | Session | What was done | Next |
|---|---|---|---|
| 2026-09-10 | Planning (claude.ai) | Reviewed brief; researched hosting/DB options; wrote CLAUDE.md and this plan | M0.1 |
| 2026-09-10 | Planning (claude.ai) | Created client-facing summary + budget docx; added D-16, D-17; updated M0.2 and Appendix A | M0.1 |
| 2026-09-10 | Build (claude.ai) | Scaffold with fake modules: M1.1, M1.2, M1.3a, M1.4, M2.1, M2.4, M2.5. Initial migration 13a53e9a5687. Verified on SQLite and PostgreSQL 16; fixed seed values too long for VARCHAR(20) (D-22) and deprecated get_engine in env.py. 46 tests pass. | W1–W6 locally, then M2.2 |
| 2026-09-11 | Build (Claude Code, Windows) | Resolved merge-conflict markers left in CLAUDE.md and docs/PROJECT_PLAN.md by commit `6647a22 mergeAll`; removed the stale root `PROJECT_PLAN.md` duplicate (docs/ copy is the single living doc). W1/W2 confirmed done (42 passed, 4 skipped; `/dev/wiring` OK on SQLite). W3–W6 marked POSTPONED. Added D-23 (admin scope), Backlog content-editor phase 2, and a Risk that PostgreSQL-only bugs stay uncaught until W5. | M3.1 design system after developer approves the design approach |
| 2026-09-11 | Build (Claude Code, Windows) | M3.1 done: design system in `static/css/main.css` (tokens, buttons, cards, `.ph` placeholders, hero, slot grid, nav, footer, sticky actions, reduced-motion). `base.html` gained skip link, meta description, scripts block. 42 passed, 4 skipped. | M3.2 homepage sections |
| 2026-09-11 | Build (Claude Code, Windows) | M3.2 done: full homepage (`index.html` + `partials/_macros.html`, `partials/footer.html`), all 9 sections, content from `turf_settings` with visible TODO(owner) notes for every gap. `TurfSettings.current_or_default()` added. Reveal animation made progressive-enhancement (`.reveal-on`) so content is visible without JS. Fixed mobile horizontal overflow (grid `minmax(0,1fr)`, `.ph` min-width:0). 49 passed, 4 skipped. | M3.3 nav + sticky mobile bar |
| 2026-09-11 | Build (Claude Code, Windows) | M3.3 done: `partials/nav.html`, `partials/sticky_actions.html`, `static/js/main.js` (header state, mobile menu). Verified at 375px in the browser: hamburger + full-screen menu (open/close/Esc/link-close, scroll lock), persistent WHATSAPP+BOOK NOW bar, no horizontal scroll. Dev server now runs with `--debug` for template/code reload. 51 passed, 4 skipped. M3 complete. | M4.1/M4.2 |
| 2026-09-11 | Docs (Claude Code, Windows) | CR-1 recorded (self-sufficient: bKash payments, auto-confirm, SMS/email outbox, slot holds, cron jobs, admin manual bookings + refunds). Documentation only — no code touched. Updated CLAUDE.md (what this is, 6 payment/notification hard rules, per-milestone push rule) and the plan: §2 constraints, D-05/D-08/D-11 updated, D-15–D-17 marked superseded, D-24…D-33 added, §4 accounts, §5 file map / data model / service contracts / routes / env names, M2.6–M2.7, M5.6–M5.7, M8.5–M8.7, M9.7–M9.8, new M10/M11/M12, execution order, §7 QA, §8 handover, C-21…C-27, Appendix B, Backlog, Risks. | Repricing agreement (C-27) then M4.2; M10 gated on C-27, M12 on merchant approval (C-21) |

---

## Appendix A: message to send the client

> Hi! To start building the TTURFZONE website, I need a few things from you.
>
> By tonight:
> 1. The domain name you want (for example tturfzone.com) and your full name, email, phone and address for registering it in your name.
> 2. Read and sign the attached project summary. It explains that the domain and hosting (normally Tk 4,200 to 5,500 per year, maximum Tk 7,000) are paid separately from the Tk 10,000 website fee.
>
> By tomorrow 9 AM:
> 3. Your slot times and opening hours. I'm planning 90-minute slots from 6:00 AM to 12:00 AM.
> 4. Prices for each slot, and whether day/night or weekend prices are different.
> 5. How many days ahead people can book.
> 6. Your booking and cancellation rules.
> 7. Phone number for calls and the WhatsApp number for booking messages.
> 8. Exact address and your Google Maps location link.
> 9. Your email for the admin login, and how quickly you usually reply to booking requests.
>
> By tomorrow 6 PM:
> 10. Logo (best quality you have).
> 11. 10 to 15 original photos straight from your phone (day, night with lights, full field, facilities). Please don't download them from Facebook, it lowers quality.
> 12. A short video if you have one.
> 13. List of facilities you actually have (parking, changing room, water, café, etc.).
> 14. A short description of your turf in 2 to 4 sentences.
> 15. Any real customer reviews you're happy to show.

## Appendix B: questions for the hosting company (ask before paying)

1. Does this plan support Python web apps (cPanel "Setup Python App" / Passenger)? Which Python versions? (Need 3.10 or newer.)
2. Do I get SSH or terminal access, with git?
3. Can I `pip install` packages, including `psycopg` for PostgreSQL?
4. Does the plan include PostgreSQL databases in cPanel? If not, can my app connect out to an external PostgreSQL server on port 5432?
5. Is free SSL (AutoSSL / Let's Encrypt) included for the domain and www?
6. Where is the server located?
7. How often are backups taken, how long are they kept, and can I restore them myself?
8. Limits on RAM, CPU and entry processes? Are Python processes killed after some time?
9. Renewal price after the first year, for hosting and for a .com domain?
10. Can the account be in my client's name while I manage it?
11. (CR-1) Can I run cron jobs, and at a once-a-minute interval?
12. (CR-1) Is outbound HTTPS (port 443) to external APIs allowed (bKash, an SMS API)?
13. (CR-1) Does the plan include email mailboxes and SMTP sending? What is the hourly/daily send limit?
14. (CR-1) Can I set custom DNS TXT records for SPF and DKIM?
