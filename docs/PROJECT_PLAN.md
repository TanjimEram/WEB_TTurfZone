# TTURFZONE project plan (living document)

> For Claude: this file is the project's memory across sessions and accounts. Read "Resume here" first. Update it in the same commit as the work (rules in CLAUDE.md). Never write passwords, API keys or connection strings in this file.

## Resume here

| Field | Value |
|---|---|
| Phase | M3 homepage complete. **CR-1 recorded** (self-sufficient: online payments, auto-confirm, SMS/email, holds, cron jobs). Scaffold done locally; waiting on hosting money for real deploy |
| Last completed | **M7.5**: 404/500 pages + handlers, accessibility pass (aria on flash / form errors / slot grid / admin buttons, heading order, contrast). 145 passed, 4 skipped (2026-09-11). Before: M5 admin, CR-2, M4.3–M4.5 |
| Next task | **Decision.** (a) **M4.6** — apply CR-2 (auto-confirm, drop PENDING) — needs C-28. (b) **M2.6** — CR-1 schema — needs C-27. (c) **M7.3** — SEO / OpenGraph / favicon / JSON-LD (confirmed info only, no assets needed). (d) **M6** — deploy current build (needs hosting). (e) **M7.1/M7.2** — real assets + lightbox (needs owner photos). |
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
- Definition of done (CR-2): on a phone, a customer selects a date and an available 90-minute slot, submits name + phone, pays the Tk 500 bKash advance, and the booking is **confirmed by the site with no owner action**. A taken slot cannot be booked. The owner logs in securely and can cancel, block slots, and add phone/walk-in bookings, but is never required for a normal booking. Production runs on HTTPS with the production database connected; duplicate-booking conflicts tested. Interim before bKash (M10): auto-confirm free or form closed (C-28).
- Original brief §19 (manual confirm) is superseded by CR-1 + CR-2.

## 2. Global constraints (from the brief; change only through a CR)

- Payment (CR-1 + CR-2, overrides brief §2): **the website confirms every booking itself — no manual owner step.** An empty slot can be booked; a taken one cannot. Confirmation is by a **Tk 500 bKash advance** (verified server-to-server), balance paid on site. `PAYMENTS_ENABLED=false` (interim, pending C-28) = auto-confirm with no payment; `true` = the advance. No payment data is ever trusted from a redirect or query string.
- Statuses: PENDING (legacy — customer requests until M4.6 removes it; still used by admin?), PENDING_PAYMENT (hold while the customer pays the advance, CR-1), CONFIRMED (booked, unavailable to others), REJECTED (declined, slot free again), EXPIRED (advance hold ran out, CR-1), CANCELLED (cancelled after confirmation, CR-1), BLOCKED (owner prevents booking).
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
| D-05 | ~~Manual mode: a PENDING request holds its slot until the owner confirms or rejects; max 2 future PENDING per phone.~~ **Superseded by CR-2** — there is no manual confirmation. A booking is `CONFIRMED` on creation (free/interim) or `PENDING_PAYMENT` → paid → `CONFIRMED` (bKash). Slot conflict is entirely the DB's job. The per-phone cap idea moves to a rate limit if abuse appears (Backlog). Still true until M4.6 ships. | CR-2: the owner wants zero manual steps. | Superseded (CR-2); current code still creates PENDING until M4.6 |
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
| D-24 | `PAYMENTS_ENABLED` config flag (default `false`). **CR-2 changes the `false` meaning:** `false` = bookings auto-confirm with **no payment** (interim launch, cash on site — pending C-28); `true` = Tk 500 bKash advance holds then confirms. Never a manual owner-confirm step. Switches to `true` after bKash merchant approval (M12). | Ship an autonomous site before merchant approval; one switch to turn on the advance. | Final (CR-1, amended by CR-2) |
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
- Built: `SLOT_TIMES`, `SLOT_MINUTES`, `TZ`, `now_dhaka()`, `today_dhaka()`, `slot_label()`, `get_day_availability()` (no past/window rules yet), and (M4.2) `booking_window(today, days)` + `date_chip_label(d, today)`. M2.2 adds `is_valid_slot`, `is_bookable` and the past/window state.
- `SLOT_TIMES: list[datetime.time]` (the 12 slots), `SLOT_MINUTES = 90`, `TZ = ZoneInfo("Asia/Dhaka")`
- `now_dhaka() -> datetime`
- `slot_label(t: time) -> str` returns `"06:00 AM"` style
- `is_valid_slot(t: time) -> bool` (built M2.2)
- `booking_window(today: date, days: int) -> list[date]` (today plus the next `days - 1` days) (built M4.2)
- `slot_start(d, t) -> datetime` (Dhaka-aware); `is_within_window(d, now=None, days=None) -> bool` (built M2.2)
- `is_bookable(d: date, t: time, now: datetime | None = None, days: int | None = None) -> bool` (valid slot, slot start in the future, date inside window). `days` defaults to `turf_settings.booking_window_days`. (built M2.2)
- `get_day_availability(d: date) -> list[dict]` returns `{"time": "06:00", "label": "06:00 AM", "state": "available|pending|booked|blocked|past", "price_bdt": int | None}`. No customer data. CR-1: a live `PENDING_PAYMENT` hold (not past `hold_expires_at`) reports `state: "pending"`; expired holds report `available`.

`services/bookings.py`
- Built (M2.3): `save_booking` (commits; uq_active_slot IntegrityError → SlotUnavailableError), `generate_booking_code`, `normalize_phone`, `create_booking_request(name, phone, booking_date, slot_time) -> Booking` (validation + `is_bookable` gate + per-phone future-PENDING cap; inserts PENDING), `confirm_booking` (PENDING only), `reject_booking(id, note=None)` (PENDING/CONFIRMED → REJECTED), `block_slot(date, time, reason)`, `unblock_slot(id)`, `BookingValidationError.errors`, `InvalidTransitionError`. All commits go through `save_booking`.
- Not built yet: `dashboard_summary(today) -> {today, pending_count, upcoming}` (M5.2).
- CR-1 (M2.7 / M10) will extend: `create_booking_request(..., *, email=None, source="online")` — expire this slot's stale holds in the same transaction (D-26); payment mode inserts `PENDING_PAYMENT` with `hold_expires_at`, `amount_due_bdt`. `confirm_booking` also from `PENDING_PAYMENT`, and idempotent. Add `cancel_booking(id, note=None)` (CONFIRMED → CANCELLED, frees the slot, queues a cancellation notice) and `expire_stale_holds(*, booking_date=None, slot_time=None, now=None) -> int` (PENDING_PAYMENT past `hold_expires_at` → EXPIRED; scoped inside `create_booking_request`, unscoped for the cron job).

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
- [x] M2.2 `services/slots.py`: `is_valid_slot`, `slot_start`, `is_within_window(d, now=None, days=None)`, `is_bookable(d, t, now=None, days=None)` (valid slot + start in the future + date inside window), `_as_dhaka` (naive → Dhaka). `get_day_availability(day, now=None)` now marks passed slots `"past"`. `/api/availability` rejects out-of-window / past dates with 400 (client never trusted to stay in the window). `days` defaults to `turf_settings.booking_window_days` (added kwarg beyond the §5.3 signature so tests stay pure). `tests/test_slots.py` +12 (frozen `now`); `tests/test_availability_api.py` reworked to a dynamic in-window date + 2 out-of-window 400 tests. 76 passed, 4 skipped. (2026-09-11)
- [x] M2.3 `services/bookings.py` + `tests/test_bookings.py`: `normalize_phone` (01…/+880…/880… → 01…), `create_booking_request` (name + phone validation reported together, `is_bookable` gate, per-phone future-PENDING cap from `turf_settings.max_pending_per_phone`, `SlotUnavailableError` on a taken slot), `confirm_booking` (PENDING only → `InvalidTransitionError`), `reject_booking` (PENDING/CONFIRMED → REJECTED, frees the slot), `block_slot` / `unblock_slot`, `BookingValidationError.errors`, `InvalidTransitionError`. 26 tests. 102 passed, 4 skipped. (2026-09-11) M2.3 = last non-CR-1 booking-rules task.
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

- [x] M4.1 `routes/api.py` `/api/availability` + `tests/test_availability_api.py`: bad date and missing date → 400; response is `Cache-Control: no-store`; slot shape is `time/label/state/price_bdt` only; no customer name or phone in the body; each state (available/pending/booked/blocked) shown. Booking-window rejection waits on M2.2. 54 passed, 4 skipped. (2026-09-11)
- [x] M4.2 `static/js/booking.js` + `partials/slot_picker.html`: server-rendered date chips for the booking window (Dhaka time, D-10), fetch `/api/availability` per date, 12 slot buttons with states, disabled slots use the real `disabled` attribute (not focusable/clickable), loading skeleton, "Try again" on fetch error, `.slot--selected` highlight, stale-response guard. Progressive enhancement: `[data-fallback]` (link to `/book` + WhatsApp) shows without JS. Homepage `#book` mounts it with a Continue button → `/book?date=&slot=`; `/book` mounts it with `picker_continue=false` and preselects from the query string. New `GET /book` route + `booking.html` (details form body is a placeholder note pending M4.3). `services/slots.py` gained `booking_window()` + `date_chip_label()` (M2.2 still owns `is_valid_slot`/`is_bookable`). Tests: `tests/test_slots.py` (3), `tests/test_public_routes.py` (7), `tests/test_availability_api.py` (from M4.1). 64 passed, 4 skipped. (2026-09-11)
- [x] M4.3 `booking.html` details form (name, phone) below the picker; hidden `date`/`slot` kept in step with the picker by `booking.js` (submit disabled until a slot is chosen). `POST /book` (CSRF via Flask-WTF): re-validates through `create_booking_request`; `BookingValidationError` → 400 re-render with per-field errors and the entered values kept; `SlotUnavailableError` → 409 re-render with "that slot was just taken" (picker reloads and shows it booked). (2026-09-11)
- [x] M4.4 `booking_success.html`: "Booking request received", booking ID, date, time (90 min), name, amber **Pending** pill, `confirm_time_text` (TODO note when unset), **Chat on WhatsApp** button (wa.me deep link with prefilled `Booking ID / Date / Time` text; TODO note when no number). Read once from `session["booking_request"]` (D-11); refresh → redirect home. (2026-09-11)
- [x] M4.5 `tests/test_public_routes.py` +10: happy path (302 → success, PENDING row, code on page), invalid phone / blank name re-render form (no row created), taken slot → 409 friendly error, past slot → 400 no row, missing slot → 400, `/book/success` with no session → home, one-time only (refresh redirects), WhatsApp link present/absent by settings. 112 passed, 4 skipped. Browser-verified the full flow at 375px. (2026-09-11)

Done when: the whole flow takes under a minute on a phone-sized viewport, and a duplicate attempt shows a friendly error.

- [ ] M4.6 (CR-2) Remove the manual `PENDING` path: `create_booking_request` → `CONFIRMED` when `PAYMENTS_ENABLED` is false, `PENDING_PAYMENT` when true (never `PENDING`). `booking_success.html` wording: "Booking confirmed" + "Tk 500 advance due / paid, balance on site". Drop the per-phone PENDING cap. Depends on M2.6. Blocked by C-28 (interim free vs closed).

### M5 Admin (Day 1, 18:00 to 22:00)

- [x] M5.1 `services/auth.py` (`verify_admin`, `login_admin`/`logout_admin` — `session.clear()` on both, `current_admin`, `safe_next`, `login_required`), `routes/admin.py` (GET/POST `/admin/login` generic error, `POST /admin/logout`, all pages `@login_required`, `?next=` limited to `/admin` paths), `templates/admin/base_admin.html` (own chrome, `noindex`), `login.html`, `static/css/admin.css`. Stub `dashboard`/`bookings`/`calendar` so the nav resolves. `tests/test_admin_routes.py` (15). 127 passed, 4 skipped. Browser-verified login → dashboard. (2026-09-11)
- [x] M5.2 `bookings.dashboard_summary(today)` + `bookings_for_day(day)`. Dashboard: 3 stat cards (bookings today / awaiting confirmation / confirmed this week), today's bookings table, next-7-days table, links to bookings + calendar. Customer name + `tel:` shown (admin only, behind login). `tests/test_admin_routes.py` +3. 130 passed, 4 skipped. (2026-09-11)
- [x] M5.3 `GET /admin/bookings?date=&status=` (exact-day + status filters, 300-row cap), table with `tel:` + `wa.me` links per customer (`_wa_number` 01→8801), status pill, code. `POST /admin/bookings/<id>/confirm` and `/reject` (CSRF, `login_required`, `InvalidTransitionError` → flash not crash, redirect back via safe `back` field). Reject/cancel has a JS confirm. `tests/test_admin_routes.py` +7. Sped the admin test fixture (cheap pbkdf2 hash). 137 passed, 4 skipped. (2026-09-11) (CR-2: "confirm" is transitional — goes with M4.6; reject/cancel stay.)
- [x] M5.4 `GET /admin/calendar?date=` — one day, 12 `.cal-slot` cards (state from `get_day_availability`, booking from `bookings_for_day`), prev/next day + date picker. Per slot: Block (reason field) for free future slots, Unblock for blocks, Confirm/Reject or Cancel for bookings, "Past" otherwise. `POST /admin/slots/block` (`SlotUnavailableError` → flash), `POST /admin/slots/<id>/unblock`. (2026-09-11)
- [x] M5.5 `tests/test_admin_routes.py` now 25 → covers logged-out redirect on every page + action, generic login failure, safe `next`, dashboard stats, list filters, confirm/reject, calendar 12 slots, block → public API sees `blocked` → unblock frees it, block on a taken slot flashes. 143 passed, 4 skipped. Browser-verified the whole admin flow. (2026-09-11)
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
- [x] M7.5 `templates/errors/404.html` + `500.html` (500 touches no DB) + `@app.errorhandler` in `app.py`; `tests/test_error_pages.py` (no stack trace, working links). Accessibility pass: flash wrapped in `role="status" aria-live="polite"` (public + admin); booking form fields get `aria-invalid` + `aria-describedby` on error; slot grid `role="group" aria-label`; calendar block field/button `aria-label`; admin confirm/reject/cancel/block buttons get contextual `aria-label` (customer + slot); admin nav `aria-current="page"`; heading order fixed (footer `h4`→`h3` + `sr-only` `h2`), verified no skips on `/`, `/book`, admin. Contrast checked (all text ≥ 5:1 on the dark ground, muted/links ≥ 7:1). Global `:focus-visible` ring + `prefers-reduced-motion` already in place. Real `<img alt>` still to come with M7.1. 145 passed, 4 skipped. (2026-09-11)

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
| C-22 | Full payment up front, or an advance percentage? | Before M10 | **Answered (CR-2): Tk 500 flat advance**, balance on site | Fills a fixed `advance_bdt = 500` |
| C-28 | Before bKash is live (M10), should the public booking form auto-confirm for free (cash on site), or stay closed until the advance works? | Before launch | Pending | CR-2. Drives `PAYMENTS_ENABLED=false` behaviour |
| C-23 | Cancellation and refund rules text (who can cancel, when, how much back) | Before M10 | Pending | CR-1. Shown on the site and used for refund decisions |
| C-24 | Hold length in minutes (default 10) and reminder timing (default 2 hours before) | Before M10 | Pending | CR-1. `HOLD_MINUTES`, `reminder_hours_before` |
| C-25 | Owner alert phone (SMS) and owner alert email | Before M11 | Pending | CR-1. `OWNER_ALERT_PHONE`, `OWNER_ALERT_EMAIL` |
| C-26 | SMS provider preference / budget (or let developer choose) | Before M11 | Pending | CR-1. Non-masking first |
| C-27 | Written agreement to the new development price and the new owner running costs (bKash fees, SMS) | Before M10 start | Pending | CR-1. Blocks M10. Reissued client summary handled by the developer (.docx outside the repo) |

## 10. Change requests

| ID | Date | Request | Type (add/remove/modify) | Impact (time, scope, price) | Affected tasks | Status |
|---|---|---|---|---|---|---|
| CR-2 | 2026-09-11 | **No manual confirmation at all.** The website decides every booking by itself: an empty slot can be booked, a taken slot cannot — the admin never has to intervene for a normal booking (but keeps full override: cancel, block, manual booking, refunds). Confirmation is by a **Tk 500 bKash advance** (bKash wired later — CR-1 M10); the balance is paid on site after the slot. Answers C-22 (advance = Tk 500 flat, not a percentage, not full payment). | modify | **Removes** the manual `PENDING → owner confirms` flow and CR-1's `PAYMENTS_ENABLED=false` "manual mode". `create_booking_request` will produce `CONFIRMED` (free/interim) or `PENDING_PAYMENT` (bKash), never `PENDING`. **Interim (before M10):** needs a call — auto-confirm free (cash on site) as a temporary launch mode, or keep the public booking form closed until bKash is live (open question, tracked as C-28). **Time:** small (mostly deletion) once M2.6/M10 land. **Price:** inside CR-1's repricing, no extra. | D-05 (superseded), D-24, CR-1 M2.6 / M4.3 / M4.4 / M10, C-22 (answered), new M4.6, M5.3 (confirm action now transitional) | Recorded 2026-09-11. Per developer: **M5 is built now against the current PENDING model and adapted when M2.6 lands** ("M5 now, adapt after"). |
| CR-1 | 2026-09-11 | Make the website self-sufficient: online payment (bKash direct gateway, server-verified), automatic confirmation, SMS + email notifications, slot holds, scheduled jobs, admin manual bookings + payments/refunds. Overrides brief §2 ("no online payment"); removes "online payments/bKash" and "SMS gateway" from brief §15 exclusions. Still excluded: customer accounts, automated WhatsApp API, multiple branches, tournaments, coupons, complex analytics, native app, AI chatbot, large CMS. | add / modify | **Time:** +2–3 dev days (4–5 total). **Price:** development must be repriced — developer estimate ~Tk 25,000 at the original daily rate, **not yet agreed with the client**; D-15…D-17 superseded pending repricing. **Owner costs:** new running costs (bKash 1.5–2% per txn, SMS ~Tk 0.25–0.40 each, possible masking-sender registration). **Blockers:** live payments need an approved bKash merchant account in the owner's name (trade licence, TIN, business bank account, NID, live URL; ~1–3 weeks). | Global constraints §2; D-05, D-11, D-15–D-17; §5 (models, services, routes, env); new M2.6, M2.7, M5.6, M5.7, M10, M11, M12; M8; §7, §8, §9, §11, §12 | Recorded 2026-09-11. Repricing + owner running-cost agreement pending (blocks M10 start). Merchant approval pending (blocks M12). Frontend (M3, M4.2) continues unaffected. |

## 11. Backlog (after MVP)

- ~~Online payment (bKash/Nagad/SSLCommerz) with advance deposit~~ — now in scope (CR-1)
- ~~Automatic confirmations (SMS or WhatsApp Business API)~~ — SMS/email now in scope (CR-1); WhatsApp API stays below
- WhatsApp Business API for confirmations and reminders (CR-1: deferred)
- Automatic refunds via the bKash refund API (CR-1: v1 records manual refunds only)
- Nagad and card payments via an aggregator (SSLCommerz / aamarPay) (CR-1)
- SMS low-balance alert to the owner (CR-1)
- Bangla notification templates (CR-1: English first)
- Per-phone / per-IP booking rate limit (replaces the dropped D-05 pending cap; only if spam appears — CR-2)
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

- Admin (M5) is built against the pre-CR-2 model: the "Confirm" action and the "Awaiting confirmation" dashboard stat go away with M4.6. Reject/cancel, block/unblock, filters and the dashboard survive unchanged.
- Rejecting/cancelling a booking does not notify the customer (no SMS/email until CR-1 M11). The confirm dialog says so.
- No admin "add a phone/walk-in booking" screen yet (CR-1 M5.6).
- Accessibility (M7.5) covered structure/aria/contrast/focus. Real `<img>` elements (M7.1) must each get a meaningful `alt`; the current `.ph` placeholders already carry `role="img"` + `aria-label`. A full screen-reader / Lighthouse run belongs in M9.1.
- `price_bdt` in the availability API is `null` until pricing is wired (M4).
- Homepage verified by tests and a 375px browser pass. A visual pass at 768px and 1280px on a real browser is still pending (do at M6.1 / developer).
- WhatsApp buttons (hero, sticky bar) render disabled and the desktop WhatsApp FAB is hidden until the owner gives the number (C-06). `tel:` link in the footer likewise waits on C-06.
- Customer booking flow works end to end in manual mode: `/book` picker + form → `POST /book` → `/book/success` (session, one-time). No online payment (CR-1 M10, gated). No email field yet (CR-1 M2.6).
- `/api/availability` reads `booking_window_days` from `turf_settings` on every request; when M7.4 lets the owner change it, in-flight pickers keep the old chips until reload (acceptable).
- The `/book` name/phone form has no client-side validation beyond `required`; the server (`create_booking_request`) is the gate. Good enough; nicer inline JS validation is polish (M7.5).
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
| 2026-09-11 | Build (Claude Code, Windows) | M4.1: `/api/availability` returns `Cache-Control: no-store`, missing `date` now 400. `tests/test_availability_api.py` +3 (missing date, not cached, slot shape). 54 passed, 4 skipped. | M4.2 booking.js slot grid |
| 2026-09-11 | Build (Claude Code, Windows) | M4.2: date + slot picker (`booking.js`, `partials/slot_picker.html`) on `/` and new `/book` page; server-rendered chips (Dhaka time), fetch per date, skeleton, retry, stale-guard, no-JS fallback. `slots.booking_window()` + `date_chip_label()`. Verified at 375px in the browser (chips scroll, slots render, select → Continue link, chip switch reloads, no h-scroll, no console errors). `tests/test_slots.py` +3, `tests/test_public_routes.py` +7. 64 passed, 4 skipped. | M2.2 slot rules |
| 2026-09-11 | Build (Claude Code, Windows) | M2.2: `is_valid_slot`, `slot_start`, `is_within_window`, `is_bookable` in `services/slots.py` (Dhaka time, frozen `now` in tests); `get_day_availability` marks `past`; `/api/availability` returns 400 for dates before today or past the window. `tests/test_slots.py` +12; `tests/test_availability_api.py` reworked to a dynamic in-window date. 76 passed, 4 skipped. | M2.3 booking rules |
| 2026-09-11 | Build (Claude Code, Windows) | M2.3: `services/bookings.py` — `normalize_phone`, `create_booking_request` (validation + `is_bookable` + per-phone PENDING cap), `confirm_booking`, `reject_booking`, `block_slot`, `unblock_slot`; `BookingValidationError`/`InvalidTransitionError`. `tests/test_bookings.py` (26). 102 passed, 4 skipped. | Decision: M2.6/M2.7 (CR-1) vs M4.3 (manual booking form) — see Resume here |
| 2026-09-11 | Build (Claude Code, Windows) | M4.3–M4.5: `booking.html` details form + `POST /book` (CSRF, server re-validation, per-field errors kept on re-render, 409 on slot race), `booking_success.html` (session one-time read D-11, Pending pill, WhatsApp deep link), `booking.js` form/picker sync. Booking form CSS. `tests/test_public_routes.py` +10. 112 passed, 4 skipped. Browser-verified: pick slot → form → submit → success → refresh redirects home; booked slot shows disabled in the grid. | M5 admin (recommended) |
| 2026-09-11 | Docs (Claude Code, Windows) | CR-2 recorded: no manual confirmation, website confirms every booking itself, Tk 500 bKash advance (wired later), admin keeps override. D-05 superseded, D-24 amended, C-22 answered, C-28 opened, M4.6 added. Developer chose "M5 now, adapt after". | M5.1 admin login |
| 2026-09-11 | Build (Claude Code, Windows) | **M5 admin complete**: M5.1 auth (`services/auth.py`, `routes/admin.py`, `base_admin.html`, `admin.css`), M5.2 dashboard (`dashboard_summary`, stat cards, today + week tables), M5.3 bookings list (date/status filters, tel:/wa.me, confirm/reject), M5.4 calendar (12-slot day view, block with reason / unblock, prev-next). `tests/test_admin_routes.py` (25). 143 passed, 4 skipped. Browser-verified: login → dashboard → filter bookings → block a slot (public API sees it) → unblock. | M4.6 / M2.6 / M7 / M6 — see Resume here |
| 2026-09-11 | Build (Claude Code, Windows) | M7.5: `errors/404.html` + `500.html` + `@app.errorhandler` (500 is DB-free); `tests/test_error_pages.py` (2). Accessibility pass across public + admin: aria-live flash regions, `aria-invalid`/`aria-describedby` on form errors, `role=group` slot grid, contextual `aria-label` on admin action buttons, `aria-current` nav, footer heading levels fixed (no skips), contrast verified. 145 passed, 4 skipped. Browser-checked the 404 page + heading audit. | M7.3 / M4.6 / M6 — see Resume here |
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
