# TTURFZONE project plan (living document)

> For Claude: this file is the project's memory across sessions and accounts. Read "Resume here" first. Update it in the same commit as the work (rules in CLAUDE.md). Never write passwords, API keys or connection strings in this file.

## Resume here

| Field | Value |
|---|---|
| Phase | **Live in production at https://tturfzone.com** (M1.3b 2026-10-13, M7.1 photos 2026-10-14) on the host's MariaDB (CR-4). **Deployed 2026-10-15:** CR-5 (no Facilities), M4.7 slot prices, M7.7 admin settings (migration `b7e3d1f04a2c` applied). **Not deployed yet:** M5.9 admin password change, CR-7 hero image (pull + restart, no migration). HTTPS redirect fixed (M8.3). CR-1 and CR-3 recorded, not built (gated on v2). |
| Last completed | **CR-7 hero image** (2026-10-14): the homepage hero now uses the supplied `assets_raw/hero.jpg` (an AI-generated aerial pitch, per its C2PA metadata) at the developer's request, built to WebP 800/1280/1920 in `static/images/hero/`; alt text labels it an illustration. Overrides the real-photos-only rule for the hero only (D-45 amended). 195 passed, 15 skipped. Before: M5.9 admin password change |
| Next task | **Deploy** (Appendix D update one-liner: pull, `pip install`, `db upgrade` — 2 migrations — `db-check`, restart), then the owner sets prices + default price in `/admin/settings` (the dashboard shows 24 missing prices until then). **Ops:** M8.3 HTTPS redirect, M8.8 off-server backup + restore test, M8.1 secret check. **Next build task: M2.6**, blocked by the v2 signature + advance (C-27/D-40). M7.6 (reviews, map) and C-31 (weekend days) wait on the owner. |
| Blocked by | **Every remaining build task is blocked on the client:** M2.6 → M2.7 → M10/M11 → M13 on the v2 signature + Tk 12,000 advance (D-40, C-27); M12 also on bKash merchant approval (C-21); M13 also on M11; M7.1 on owner assets (C-12, C-13, C-16…C-18); C-28 needs the client's confirmation of D-41. The jobs cron (M8.5) waits on M11. Backups sit on the same server until an off-server copy exists. |
| Dev environment | Windows + PowerShell. venv: `.venv\Scripts\Activate.ps1`. |
| Live URL | https://tturfzone.com (deployed 2026-10-13) |
| Repo | created by developer (private GitHub) |

Status keys: `[ ]` to do, `[x]` done, `~~struck through~~ (CR-n)` dropped by a change request.

---

## 1. Snapshot

- Client: TTURFZONE turf ground owner. Facebook: https://www.facebook.com/TTURFZONE
- Found online (confirm with owner): listed on Book My Turf BD as "T Turf Zone", 6-a-side futsal, Notin Rani ghat, New Jailkhana, inside Tripti Sporting Club.
- Reference site, inspiration only, do not copy: https://turfxsonagazi.com
- Brief: `docs/brief/TTURFZONE_Claude_Code_Project_Brief.pdf`
- Budget: originally ৳10,000 / 2 days. **CR-1 + CR-3 combined reprice to Tk 30,000 / 6 days (client summary v2, D-40, sent 2026-09-16, not yet signed).** Built with Claude Code.
- Definition of done (CR-2): on a phone, a customer selects a date and an available 90-minute slot, submits name + phone, pays the Tk 500 bKash advance, and the booking is **confirmed by the site with no owner action**. A taken slot cannot be booked. The owner logs in securely and can cancel, block slots, and add phone/walk-in bookings, but is never required for a normal booking. Production runs on HTTPS with the production database connected; duplicate-booking conflicts tested. Interim before bKash (M10): auto-confirm free or form closed (C-28).
- Original brief §19 (manual confirm) is superseded by CR-1 + CR-2.

## 2. Global constraints (from the brief; change only through a CR)

- Payment (CR-1 + CR-2, overrides brief §2): **the website confirms every booking itself — no manual owner step.** An empty slot can be booked; a taken one cannot. **Shipped (M4.6, D-41):** `PAYMENTS_ENABLED=false` (the only reachable state today) auto-confirms with no payment. **Not yet built (M2.6/M10):** `true` = a Tk 500 bKash advance, verified server-to-server, balance paid on site. No payment data is ever trusted from a redirect or query string.
- Statuses: PENDING (no longer created by the guest booking flow as of M4.6; stays available for other paths, e.g. a future admin manual booking, M5.6), PENDING_PAYMENT (hold while the customer pays the advance, CR-1, not built), CONFIRMED (booked, unavailable to others — what every guest booking becomes immediately), REJECTED (declined, slot free again), EXPIRED (advance hold ran out, CR-1, not built), CANCELLED (cancelled after confirmation, CR-1, not built), BLOCKED (owner prevents booking).
- Fixed 90-minute slots: 06:00, 07:30, 09:00, 10:30, 12:00, 13:30, 15:00, 16:30, 18:00, 19:30, 21:00, 22:30.
- Duplicate bookings are prevented on the server/database side. Client-side availability is never trusted. The rule covers PENDING_PAYMENT (CR-1, once built), PENDING, CONFIRMED and BLOCKED: the `uq_active_slot` partial unique index on PostgreSQL/SQLite, and on MariaDB (production, CR-4) the `active_slot_key` generated column + `uq_active_slot_key` unique index (D-42).
- Mobile-first. Persistent mobile actions: WHATSAPP and BOOK NOW.
- Never invent business information. Use `TODO(owner):` placeholders for missing data.
- Reviews: only genuine, owner-approved. Facebook: link only, no Facebook API.
- WhatsApp: deep link only, no paid messaging API. WhatsApp Business API stays in the Backlog (CR-1).
- Notifications (CR-1): SMS via a Bangladeshi SMS API and email via the hosting SMTP mailbox. Written to an outbox table and sent by a scheduled job with retries. A failed SMS or email never fails or rolls back a booking.
- Scheduled jobs (CR-1): cPanel cron once a minute runs Flask CLI commands to expire holds, send queued notifications and send reminders.
- Secrets only in environment variables. Passwords hashed. Admin routes protected. HTTPS in production. Customer booking data never public.
- Readable, beginner-friendly code. Separate config, models, routes, services and templates. No unnecessary dependencies.
- Excluded (updated by CR-1, CR-3): automated WhatsApp API, multiple branches, tournaments, coupons/loyalty, complex analytics, native app, AI chatbot, large CMS. (`online payments/bKash` and `SMS gateway` were removed from this list by CR-1, and `customer accounts` by CR-3 — all now in scope.)
- Customer accounts (CR-3): optional login by phone number + a one-time SMS code (no passwords stored for customers). Guest booking without an account must always remain available and is never blocked behind login — an account is never required to book.
- Visual direction (unless the owner's brand says otherwise): dark base, energetic green accent, white typography, high-contrast CTAs, large real photos, clean cards, restrained motion.

## 3. Decisions

| ID | Decision | Why | Status |
|---|---|---|---|
| D-01 | Flask + Jinja + vanilla JS + PostgreSQL. **Production database changed to MariaDB on the host by CR-4**; PostgreSQL stays supported in code | Brief §8; CR-4 | Final (amended by CR-4) |
| D-02 | Database: **MariaDB 11.4 on the cPanel host (localhost)** (CR-4). Neon is unusable because the host blocks outbound TCP 5432. PostgreSQL support stays in the code (`postgresql://` URLs, partial-index path, `pytest -m postgres`) for a possible future move. Never Supabase Free. | Was: host PostgreSQL, else Neon Free. Verified from the server 2026-10-13: "Connection refused" on every Neon IPv4 address, "Network is unreachable" on IPv6, while outbound HTTPS works. Changing hosting is not an option; MariaDB on localhost needs no outbound connection. Cost of the switch: no Neon-style automatic backups, so a mysqldump cron is required (M8.8). | Final (CR-4, 2026-10-13) |
| D-03 | App hosting: Bangladeshi cPanel hosting with Python app support (Passenger), paid in BDT, account in the owner's name. **Chosen: Cyber Developer BD shared cPanel (server srv2), Python 3.11. No SSH: commands go through cPanel's web Terminal (§4, Appendix D).** | No cold starts, bKash payment, local support, low yearly cost. Free Render/Koyeb tiers sleep, which is bad for a booking site opened from Facebook. | Final (hosting bought, 2026-10) |
| D-04 | Blocks are rows in `bookings` with status BLOCKED (reason in `admin_note`). No separate BlockedSlot table. | One partial unique index then prevents every conflict (booking vs booking, booking vs block). Brief §2 already treats BLOCKED as a booking status; brief §10 allows schema refinement. | Final unless developer objects |
| D-05 | ~~Manual mode: a PENDING request holds its slot until the owner confirms or rejects; max 2 future PENDING per phone.~~ **Superseded by CR-2, shipped M4.6** — there is no manual confirmation. A booking is `CONFIRMED` on creation (free/interim, live now) or `PENDING_PAYMENT` → paid → `CONFIRMED` (bKash, M2.6/M10, not built). Slot conflict is entirely the DB's job. The per-phone cap idea moves to a rate limit if abuse appears (Backlog). | CR-2: the owner wants zero manual steps. | Superseded (CR-2); implemented M4.6 (2026-09-30) |
| D-06 | Owner can reject a CONFIRMED booking too (shown as "Cancel") | Real customers cancel; the owner must be able to free the slot | Final |
| D-07 | Plain CSS with custom properties, no Tailwind build step | Nothing to compile on cPanel; fewer moving parts | Final |
| D-08 | Dependencies: Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF, **PyMySQL** (CR-4, D-43), python-dotenv, tzdata; dev: pytest, psycopg[binary] (only for `pytest -m postgres`, moved out of production by CR-4). CR-1 adds `requests` (D-33). `itsdangerous` (signed tokens, D-11) and `smtplib`/`email` (SMTP, D-30) ship with Flask / the stdlib. Add gunicorn only if deploying to Render. | Flask-Migrate: future schema changes on live data. Flask-WTF: CSRF protection. tzdata: zoneinfo on Windows has no timezone database. | Final (CR-1, CR-4 changes) |
| D-09 | ~~Slot times are a constant in `services/slots.py` for the MVP~~ **Superseded by CR-6:** the 12 slot start times are owner-editable in `/admin/settings` (M7.7); the constant `SLOT_TIMES` stays as the default when none are saved. Still exactly 12 slots of 90 minutes. | Was: settings-driven slot config is future work. CR-6: the owner wants to adjust timings himself. | Superseded (CR-6, 2026-10-14) |
| D-10 | Business logic uses Asia/Dhaka time (`zoneinfo`). Slots stored as local `date` + `time`; audit fields as `timestamptz`. | Server may run in UTC | Final |
| D-11 | Success / payment-result page reads the booking from the session or from a short-lived signed token (`itsdangerous`, already a Flask dependency), not a public `/booking/<code>` URL. The token carries only the booking id and a short expiry. | Brief §13: do not expose customer data publicly. A payment gateway returns the user to a fixed URL, so the session alone is not always enough — a signed, expiring token is safe. | Final (updated by CR-1) |
| D-12 | `/healthz` does not touch the database | An uptime check must not depend on (or, on Neon, wake) the database. Still right on MariaDB (CR-4) | Final |
| D-13 | Owner content (about, ~~facilities~~ (CR-5), reviews, pricing, gallery list, contact, hours) lives in one `turf_settings` row, seeded from `database/seed_data.py` | One place to edit; admin settings page (M7.4) can edit it later | Final |
| D-14 | Admin password generated by `create-admin` (20 random chars, shown once). **Since M5.9** the owner can change it from Settings (min 12 characters) and `reset-admin-password` recovers a lost one. Login rate limiting stays in the Backlog. | Fits the 2-day window; strong generated password lowers brute-force risk; the owner must be able to replace the developer-generated password at handover | Final (extended by M5.9, 2026-10-14) |
| D-15 | ৳10,000 is the development fee. Domain and hosting are billed to the owner separately and registered in the owner's name. | Recurring costs belong to the owner; clean handover | **Superseded — see D-40 (client summary v2, Tk 30,000, sent 2026-09-16, not yet signed).** Not deleted. |
| D-16 | Budget ranges shown to client: hosting Tk 3,000–4,000 (max 5,000)/yr, .com domain Tk 1,200–1,500 (max 2,000)/yr, DB/SSL/WhatsApp Tk 0. Running cost max Tk 7,000/yr; year-1 total max Tk 17,000. Nothing bought above the max without written approval. | Advance must not be spent on infrastructure | **Superseded — see D-40** (v2 running costs max Tk 12,000/yr, covers bKash fees, SMS incl. OTP). Not deleted. |
| D-18 | Dev-only diagnostics: `/dev/wiring` page and `fake-*` CLI commands, fake rows use `FK-` codes. Registered only when `ENABLE_DEV_TOOLS` (development). | Test DB connection, migrations, conflict rule and API before real features and before hosting exists | Final |
| D-19 | `scripts/serve_like_passenger.py` uses stdlib `wsgiref` to import `passenger_wsgi.application` in production mode | Rehearse cPanel loading without buying hosting; no new dependency | Final |
| D-20 | `requirements-dev.txt` adds pytest on top of `requirements.txt`; production installs only `requirements.txt` | Keep production minimal | Final |
| D-21 | `config.normalize_database_url()` converts `postgres://`/`postgresql://` to `postgresql+psycopg://` and `mysql://` to `mysql+pymysql://` (CR-4); `mysql+pymysql://` and `sqlite://` pass through | Paste host URLs unchanged | Final (CR-4 addition) |
| D-22 | Short seed fields (phone, whatsapp: 20 chars) seed as empty strings; the TODO lives in a comment | PostgreSQL rejected long placeholder text (caught by testing on Postgres) | Final |
| D-23 | Admin scope: the owner manages bookings, blocks slots, and edits settings: phone, WhatsApp, address, hours, booking rules, confirmation-page note, booking window, prices (bands + default), and **since CR-6 also the 12 slot times, the about text and the tagline**. Images, page layout and design stay with the developer. A content editor for images (hero photo, gallery upload) is a paid phase 2, in the Backlog. Reviews and the map stay developer-entered for now. | Keeps the MVP small; media handling is its own project. CR-6 added the few text/time fields the owner wants to change often. | Final (developer 2026-09-11; widened by CR-6, 2026-10-14) |
| D-17 | Payments: (1) Tk 5,000 development advance before build; (2) hosting + domain actual cost (up to Tk 7,000) before build, paid by owner directly or sent with receipts; (3) Tk 5,000 balance at handover after owner tests live site. Unused infra money returned or deducted from payment 3. 2-day clock starts after payments 1–2 and Day-1 inputs. 7 days of free fixes after handover. | Protects developer from funding infra out of the advance; protects deadline from late assets | **Superseded — see D-40** (v2 schedule: Tk 12,000 advance + hosting/SMS + Tk 9,000 Day 3 + Tk 9,000 handover; 14 days free fixes). Not deleted. |
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
| D-34 | Customer login is phone number + a one-time SMS code (OTP). No passwords are stored anywhere for customers, so there is no password-reset flow and no password hashing on the customer side. | Fewer moving parts than passwords (no reset flow, no leaked-password risk); a verified phone is exactly what the booking system already keys on, and it doubles as fraud reduction (D-38 note). | Final (CR-3) |
| D-35 | Guest booking is permanent, not a migration step. Accounts are optional forever — `/book` never checks for a session, and nothing in the booking flow requires a `customer_id`. | The client was explicit: an account must never be required to book. | Final (CR-3) |
| D-36 | Customer login sessions last 60 days (vs the owner admin session's 12 hours, `PERMANENT_SESSION_LIFETIME`, unchanged). Flask has one global session lifetime, so the customer session needs either a `before_request` override keyed on which principal is logged in, or a separate long-lived cookie from the admin session. Implementation decided at build time (M13). | A customer should not have to re-verify by SMS every visit; the owner's admin session stays short for security. | Final (CR-3); implementation approach open, M13 |
| D-37 | OTP rate limits, enforced server-side: at most 3 codes per phone per hour and 5 per day; at most 5 wrong verification attempts per code before it is invalidated. | Every code costs about Tk 0.35; an unlimited endpoint is an open SMS bill. | Final (CR-3) |
| D-38 | When a guest later creates an account with the same phone number, their past guest bookings (`customer_id IS NULL`, matching phone) are linked to the new account on signup. | Booking history should not silently vanish just because the customer signed up after the fact. | Final (CR-3) |
| D-39 | `login_codes.code_hash` stores a hash of the OTP, never the plain code, in the database or in any log line. The SMS itself is sent through the same `notifications` outbox as other messages (CR-1 D-28), so OTP delivery gets the same retry/failure handling. | Matches the "never log a secret" hard rule; reuses the outbox instead of a second sending path. | Final (CR-3); depends on the outbox existing (CR-1 M11) |
| D-40 | Client summary v2 (outside the repo, reissued 2026-09-16): Tk 30,000 development; running costs max Tk 12,000/yr; payment schedule Tk 12,000 advance + hosting/SMS costs (owner pays directly) + Tk 9,000 at Day 3 + Tk 9,000 at handover; 14 days of free fixes after handover. Supersedes the CR-1 estimate (~Tk 25,000) and D-15/D-16/D-17 (v1). Status: **sent to client, not yet signed.** | CR-3 adds a day of work and ongoing SMS cost (OTP codes) on top of CR-1's repricing; one combined figure is clearer for the client than two separate revisions. | Sent to client 2026-09-16, pending signature |
| D-41 | M4.6 implemented C-28 as **"free interim"**: while `PAYMENTS_ENABLED=false` (the only reachable state today — M10's gateway doesn't exist), `create_booking_request` confirms every valid booking immediately, no payment. Setting `PAYMENTS_ENABLED=true` now raises `NotImplementedError` rather than mislabeling a booking, since `PENDING_PAYMENT` needs M2.6/M10. | D-24 already named "free, cash on site" as the default; it is also the only option buildable before the bKash gateway exists. Developer default, not yet the client's own answer to C-28. | Final (developer, 2026-09-30); **flag to client — confirm or override via C-28** |
| D-42 | **MariaDB double-booking rule** (CR-4): a STORED generated column `active_slot_key VARCHAR(20) AS (CASE WHEN status IN ('PENDING','CONFIRMED','BLOCKED') THEN CONCAT(booking_date,' ',slot_time) END)` with a plain unique index `uq_active_slot_key`. PostgreSQL/SQLite keep the partial index `uq_active_slot` (`Index.ddl_if` keeps it off MariaDB, where it would silently lose its WHERE). The column is not mapped in the model (the app never reads it): the hand-edited initial migration creates it, an `after_create` DDL does the same for `db.create_all()` on MariaDB only, and `env.py` hides both from autogenerate on MariaDB. The initial migration was edited in place, because no production database existed yet, rather than adding a fix-up migration that would first build a WHERE-less unique index. | Equivalent to the partial index: an active row gets a non-NULL key that is unique per (date, slot); an inactive row gets NULL, and a unique index allows any number of NULLs. InnoDB's unique index does the check at insert time, so it is race-safe exactly like PostgreSQL's (10-thread test). MariaDB has no partial indexes; a trigger or an app-side check would not be race-safe. | Final (CR-4, 2026-10-13) |
| D-43 | MariaDB driver: **PyMySQL** (pure Python). Production `requirements.txt` drops psycopg. | Nothing to compile on shared cPanel (`mysqlclient` needs C headers the host may lack). SQLAlchemy's standard driver for MariaDB/MySQL. | Final (CR-4) |
| D-44 | DateTime columns always hold **UTC**. MariaDB `DATETIME` (and SQLite) store no offset, and PyMySQL **drops the offset on write without converting**, so only `utcnow()` may be written; values read back are naive and mean UTC. No code reads timestamps today. When CR-1 adds `hold_expires_at` (read and compared), add a UTC-normalising column type at that point. | Verified on MariaDB 11.4.13: a +06:00 datetime was stored as its wall-clock time, unconverted. | Final (CR-4) |
| D-45 | **Owner photos are static files managed by the developer** (D-23): originals in `assets_raw/` (gitignored), `scripts/build_images.py` makes WebP at 400/800/1280 (never upscaled, EXIF stripped) plus the logo emblem, favicon, apple-touch-icon and `og:image`; the list, order and alt text live in `routes/public.py` `PHOTOS`. `turf_settings.gallery` (D-13) is left unused. Pillow is a **dev-only** dependency (`requirements-dev.txt`). Only real photos of the ground are used for the about section, gallery and share image. **Exception (CR-7):** the hero uses the supplied AI-generated aerial pitch (`hero.jpg`) at the developer's request; its alt text calls it an illustration and never claims it shows this ground. | Production only serves the built files, so nothing to install or compile on cPanel; one script makes re-adding photos repeatable; a hardcoded list is simpler than a DB field nobody edits (owner photo uploads are the paid phase-2 content editor, Backlog). A picture of a different pitch would misrepresent what a customer is booking. | Final (M7.1, 2026-10-14; hero exception CR-7) |
| D-46 | **Weekend = Friday and Saturday** (`services/pricing.WEEKEND_DAYS`), Bangladesh's official weekend. Used only to pick weekday vs weekend price bands. | Developer decision 2026-10-14; it's a business rule, so the owner should confirm (C-31). Changing it means editing the constant and its two display labels (`DAY_KINDS`). | Assumed (2026-10-14), confirm via C-31 |
| D-47 | **Price resolution order** (`services/pricing.resolve`), one function used by the slot grid, the API, the homepage price list and the admin preview: (1) a band for this day type (weekday/weekend) that lists the slot; (2) else an all-days band that lists it; (3) else `turf_settings.default_price_bdt`; (4) else none, shown as "price on request" (only before the owner sets prices). Within (1) and (2) the band higher in the owner's list wins. | A specific-day band overriding an all-days band is how the owner thinks ("evenings 4500, weekend evenings 5000"); list order only breaks ties, so reordering is rarely needed. One resolver means the price list and the slot grid can never disagree. The default price guarantees every slot has a price once the owner saves settings. | Final (developer, 2026-10-14) |
| D-48 | **Slot times live in `turf_settings.slot_times`** (JSON list of 12 "HH:MM"; NULL = the built-in `SLOT_TIMES`), read through `services/slots.slot_times()` everywhere (picker, API, booking validation, admin calendar, pricing). Still exactly 12 slots of 90 minutes: the form requires them in order and at least 90 minutes apart. In the settings form, band checkboxes carry the slot's **position** (0–11), so a band follows its slot when the owner retimes it in the same save. A change is refused, listing the booking codes, when any PENDING/CONFIRMED/BLOCKED booking from today onwards sits at a removed time; past bookings never block it. | CR-6. Positions keep bands and times in step without a separate remapping step. Refusing (rather than auto-moving bookings) keeps the owner in control of customers' bookings. | Final (CR-6, 2026-10-14) |
| D-49 | **Password changes sign out other sessions** via a fingerprint in the session: at login the session stores the first 16 hex characters of SHA-256 of the admin's `password_hash` (`admin_pw`); `current_admin()` drops any session whose fingerprint no longer matches. A change from Settings refreshes the fingerprint in the current session only, so that browser stays signed in; `reset-admin-password` changes the hash, so every session ends. Minimum new-password length 12. | Flask's sessions are signed cookies with nothing server-side to revoke; deriving a stamp from the hash needs no new column or migration and covers the CLI reset for free (the same approach as Django's session auth hash). Sessions created before this deploy have no stamp, so the owner is asked to sign in once more. | Final (developer, 2026-10-14) |

## 4. Infrastructure and accounts (no secrets here)

| Service | Purpose | Account owner | Status | Notes |
|---|---|---|---|---|
| Domain | Website address | Owner is registrant; developer has access | **Bought: tturfzone.com** | Record renewal date and renewal price here once known. |
| Hosting (BD cPanel, Python) | Runs Flask app | Owner's email; login shared privately | **Live: Cyber Developer BD shared cPanel, server srv2** | Python 3.11.16 + Passenger. App root `/home/tturfzo1/tturfzone`; venv `/home/tturfzo1/virtualenv/tturfzone/3.11`. **No SSH:** run commands in cPanel → Terminal, one single-line command at a time (it mangles multi-line pastes and heredocs). cPanel Git Version Control rejects tokens in the clone URL, so the repo is cloned and pulled with `git` in Terminal (Appendix D). Env vars set in the cPanel Python App UI reach the web process only, not Terminal. Outbound TCP 5432 blocked (CR-4); outbound HTTPS works. |
| MariaDB 11.4 (on the host) | Production DB (CR-4) | Owner's hosting account | **Live: MariaDB 11.4.13, localhost, migration 13a53e9a5687** | Created in cPanel → MySQL Databases, user with ALL PRIVILEGES. URL in `~/.tturfzone_db` (chmod 600) for Terminal, in the Python App env for the web process; `~/.my.cnf` (chmod 600) for mysqldump. Round trip ~1 ms, tables utf8mb4_unicode_ci. Daily 03:00 mysqldump, 14-day retention, **on the same server** (off-server copy pending, M8.8). |
| GitHub (private repo) | Code | Developer now; **transferred to the owner's account at handover, developer re-added as collaborator** (M9.7) | Created (private); cloned on the host | |
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
├── requirements-dev.txt      # + pytest, psycopg (postgres tests only, CR-4)
├── pytest.ini                # pythonpath, postgres + mariadb markers
├── .env.example
├── .gitignore                # .env, .venv, __pycache__, instance/, *.sqlite
├── docs/
│   ├── PROJECT_PLAN.md
│   └── brief/TTURFZONE_Claude_Code_Project_Brief.pdf
├── models/
│   ├── __init__.py           # exports Admin, Booking, TurfSettings; CR-1: Payment, Notification; CR-3: Customer, LoginCode
│   ├── _time.py              # utcnow()
│   ├── admin.py
│   ├── booking.py            # CR-1: new statuses + hold_expires_at, amount_due_bdt, customer_email, source; CR-3: customer_id
│   ├── turf_settings.py
│   ├── payment.py            # CR-1
│   ├── notification.py       # CR-1 (outbox)
│   ├── customer.py           # CR-3
│   └── login_code.py         # CR-3
├── routes/
│   ├── __init__.py
│   ├── public.py             # blueprint "public": /, /book, /book/success, /healthz
│   ├── dev.py                # blueprint "dev" (development only): /dev/wiring + fake-data buttons
│   ├── api.py                # blueprint "api": /api/availability
│   ├── payments.py           # CR-1 blueprint "payments": /pay/start, /pay/bkash/callback, /pay/result
│   ├── account.py            # CR-3 blueprint "account": /account/login, /verify, /logout, /bookings, /profile
│   └── admin.py              # blueprint "admin": /admin/... (CR-1: manual booking, payments list, refunds; CR-3: customers list)
├── services/
│   ├── __init__.py
│   ├── slots.py              # slot constants, Dhaka time, bookability, day availability
│   ├── bookings.py           # create/confirm/reject/block/unblock, validation, codes; CR-1: expire holds, PENDING_PAYMENT
│   ├── payments/             # CR-1: base.py (PaymentGateway ABC), bkash.py, __init__.py (get_gateway())
│   ├── notifications.py      # CR-1: queue_*, render templates, send_due() used by the job
│   ├── jobs.py               # CR-1: expire_holds(), send_notifications(), send_reminders()
│   ├── otp.py                 # CR-3: request_code, verify_code, rate limits, customer_login_required
│   ├── customers.py           # CR-3: get_or_create_customer, link_guest_bookings, bookings_for_customer
│   ├── settings.py           # M7.4/M7.7: owner settings parse/validate/save, slot-time stranding check, price preview
│   ├── pricing.py            # M4.7: price bands -> one price per slot (D-47), weekend Fri+Sat (D-46), homepage rundown
│   ├── fake_data.py          # FK- fake bookings, double-booking probe (development)
│   └── db_health.py          # check_database() used by db-check and /dev/wiring
│   └── auth.py               # login_required, verify_admin (owner admin only - unchanged by CR-3)
├── templates/
│   ├── base.html
│   ├── partials/             # nav, footer, sticky_actions, slot_grid, flash
│   ├── index.html
│   ├── booking.html
│   ├── booking_success.html
│   ├── payment_result.html   # CR-1: paid / failed / cancelled / timed-out
│   ├── errors/404.html, errors/500.html
│   ├── account/ login.html, verify.html, bookings.html, profile.html   # CR-3
│   └── admin/ base_admin.html, login.html, dashboard.html, bookings.html, calendar.html, settings.html,
│              booking_new.html (CR-1 manual booking), payments.html (CR-1 list + refund record),
│              customers.html (CR-3 list + booking counts)
├── static/
│   ├── css/ main.css, admin.css
│   ├── js/ booking.js, gallery.js, reveal.js, admin.js
│   ├── images/ photos/<name>-{400,800,1280}.webp, logo-emblem-96.webp, og-image.jpg   # built by scripts/build_images.py (M7.1)
│   └── icons/
├── notification_templates/   # CR-1: plain-text SMS + email bodies (English; Bangla later)
├── scripts/
│   ├── serve_like_passenger.py   # cPanel/Passenger simulation
│   └── build_images.py           # M7.1: assets_raw/ (gitignored originals) -> static/ WebP/PNG/JPEG (Pillow, dev-only)
├── database/
│   ├── migrations/           # Flask-Migrate (Migrate(app, db, directory="database/migrations"))
│   └── seed_data.py          # TurfSettings defaults with TODO(owner) placeholders
└── tests/
    ├── conftest.py                 # app (SQLite in-memory), client, pg_url
    ├── test_config.py, test_app_wiring.py, test_passenger_entrypoint.py
    ├── test_booking_rules_db.py, test_fake_data.py, test_availability_api.py
    ├── test_db_health.py, test_cli.py, test_dev_tools.py, test_seed_data.py
    ├── test_postgres.py            # @pytest.mark.postgres: migrations, partial index, 10-thread race
    ├── test_mariadb.py             # CR-4 @pytest.mark.mariadb: generated column + unique index, 10-thread race, utf8mb4/Bangla, up/downgrade
    ├── test_slots.py               # M2.2
    ├── test_bookings.py            # M2.3
    ├── test_holds.py               # CR-1 M2.7: hold expiry inside booking creation (+ @pytest.mark.postgres)
    ├── test_payments.py            # CR-1 M10: gateway interface + fake bKash, verification, idempotency
    ├── test_payment_routes.py      # CR-1 M10: /pay/* with a fake gateway
    ├── test_notifications.py       # CR-1 M11: outbox queue, retries, failure never rolls back a booking
    ├── test_jobs.py                # CR-1 M11: expire_holds / send_notifications / send_reminders
    ├── test_sandbox.py             # CR-1: @pytest.mark.sandbox, real bKash sandbox, skipped without creds
    ├── test_otp.py                  # CR-3 M13: rate limits, expiry, wrong-attempt lockout, hashed storage
    ├── test_account_routes.py       # CR-3 M13: login/verify/logout/bookings/profile, guest booking unaffected
    ├── test_public_routes.py       # M4
    └── test_admin_routes.py        # M5 (+ CR-1 M5.6/M5.7; CR-3 admin customers list)
```

### 5.2 Data model

**admins**: id (PK), username (unique, not null), password_hash (not null, werkzeug `generate_password_hash`), created_at (timestamptz).

**bookings**: id (PK), booking_code (unique, e.g. `TZ-7K3M9Q`), customer_name (nullable for BLOCKED), phone (nullable for BLOCKED, normalized `01XXXXXXXXX`), booking_date (date), slot_time (time), status (see below), admin_note (text, nullable; block reason or rejection note), created_at, updated_at (timestamptz).
CR-1 adds: `hold_expires_at` (timestamptz, nullable — set for PENDING_PAYMENT), `amount_due_bdt` (int, nullable), `customer_email` (string, nullable, optional), `source` (`online|phone|walk_in`, default `online`).
CR-3 adds: `customer_id` (FK → customers, **nullable** — null for every guest booking; a guest booking is never required to link to an account).

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

**MariaDB (production, CR-4, D-42).** MariaDB has no partial indexes, so the same rule is a STORED generated column plus a plain unique index:

```sql
active_slot_key VARCHAR(20) GENERATED ALWAYS AS (
  CASE WHEN status IN ('PENDING','CONFIRMED','BLOCKED') THEN CONCAT(booking_date, ' ', slot_time) END
) STORED,
UNIQUE KEY uq_active_slot_key (active_slot_key)
```

An active row gets `'2030-05-05 19:30:00'`, any other row NULL, and the unique index allows many NULLs. A second active row raises error 1062 `Duplicate entry ... for key 'uq_active_slot_key'`, which `_is_slot_conflict` turns into `SlotUnavailableError`. **When CR-1 adds `PENDING_PAYMENT`, the migration must change both the partial-index WHERE and this expression** (`ALTER TABLE bookings MODIFY active_slot_key ...`).

Other MariaDB facts (all checked by `tests/test_mariadb.py`):
- Every table is `utf8mb4` / `utf8mb4_unicode_ci` (`extensions.MYSQL_TABLE_OPTIONS`) whatever the server default (the local test server is latin1 on purpose). `_ci` makes `booking_code` and `admins.username` uniqueness case-insensitive; codes are generated upper-case, so no effect.
- Indexed strings are far below InnoDB's 3072-byte key limit (longest: `admins.username`, 50 chars × 4 bytes).
- `JSON` is LONGTEXT with a `json_valid` CHECK; Bangla round-trips through VARCHAR, TEXT and JSON.
- `DateTime(timezone=True)` is plain `DATETIME`: UTC with no offset (D-44).
- Table names are all lower-case (MariaDB on Linux is case-sensitive about them).

**payments** (CR-1): id (PK), booking_id (FK bookings, not null), gateway (string, e.g. `bkash`), merchant_invoice (string, **unique** — our idempotency key), gateway_payment_id (string, **unique**, nullable until "create payment" succeeds), amount_bdt (int), status (`INITIATED|SUCCESS|FAILED|CANCELLED|REFUNDED`), raw_response (JSON, **no secrets/tokens**), created_at, updated_at (timestamptz).

**notifications** (CR-1, outbox): id (PK), booking_id (FK, nullable), channel (`sms|email`), recipient (string), template (string, name under `notification_templates/`), body (text, rendered), status (`QUEUED|SENT|FAILED`), attempts (int, default 0), last_error (text, nullable), send_after (timestamptz — reminders and retry backoff), sent_at (timestamptz, nullable), created_at (timestamptz).

**customers** (CR-3): id (PK), phone (string, **unique**, normalized `01XXXXXXXXX`), name (string, nullable), email (string, nullable, optional), phone_verified_at (timestamptz, nullable — set the first time an OTP is verified), created_at, last_login_at (timestamptz, nullable).

**login_codes** (CR-3): id (PK), phone (string), code_hash (string, **the OTP is never stored in plain text**), expires_at (timestamptz — created_at + 5 minutes), attempts (int, default 0), consumed_at (timestamptz, nullable — set once verified, so a code can't be reused), created_at (timestamptz). Indexed on `(phone, created_at)` for the rate-limit counts (D-37).

**turf_settings** (single row, id = 1): turf_name, tagline, about_text, phone, whatsapp (digits with country code, e.g. `8801XXXXXXXXX`), address, map_embed_url, map_link, facebook_url, opening_hours_text, booking_rules_text, confirm_time_text, booking_window_days (int, default 14), max_pending_per_phone (int, default 2), pricing (JSON), default_price_bdt (int, nullable, M4.7 — the price for slots no band covers), slot_times (JSON, nullable, CR-6/M7.7 — 12 "HH:MM" starts; NULL = built-in default), facilities (JSON, **unused since CR-5**: kept so the section can return without a migration), reviews (JSON), gallery (JSON), updated_at.

Pricing JSON shape (M4.7; final values from C-02). A list of bands in the owner's order; resolved by `services/pricing.resolve` (D-47):

```json
[{"label": "Morning", "slots": ["06:00", "07:30", "09:00"], "days": "all", "price_bdt": 0}]
```

`days` is `all`, `weekday` or `weekend` (weekend = Friday + Saturday, D-46). `slots` lists slot start times. A slot no band covers gets `default_price_bdt`; with no default it has no price ("price on request"), which the admin flags.

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

`services/settings.py` (M7.4, M7.7)
- `parse_settings_form(form) -> dict` validates every field (no writes); `save_owner_settings(form)` also refuses stranded bookings (`stranded_bookings(new_times)`) and writes; both raise `SettingsValidationError(.errors)`
- `preview_prices(form)` lenient preview of unsaved prices; `price_summary(table)` / `current_price_summary()` add `missing` / `defaulted` counts for the admin warnings

`services/pricing.py` (M4.7)
- `WEEKEND_DAYS = (4, 5)` (Fri, Sat; D-46), `day_kind(d) -> "weekday"|"weekend"`
- `resolve(bands, default_price, slot_key, kind) -> {"price_bdt": int|None, "band": label|None}` — the one resolution rule (D-47)
- `price_table(settings, times=None) -> {"weekday": [row], "weekend": [row]}` (row: time, label, price_bdt, band) — used by the admin preview
- `prices_for_day(settings, d) -> {"06:00": int|None, ...}` — used by `/api/availability`
- `rundown(settings) -> [{"days", "rows": [{start, end, price_bdt, band}]}]` — homepage price list; consecutive equal slots merged; one "Every day" block when weekday == weekend; `[]` before any price is set

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
- M5.9: `change_password(admin, current, new, confirm)` (raises `PasswordChangeError(.errors)`; min `MIN_PASSWORD_LENGTH` = 12), session fingerprint `admin_pw` checked in `current_admin()` (D-49)
- Owner admin login only. Unaffected by CR-3 — the owner never uses OTP, customers never use a password.

`services/otp.py` (CR-3)
- `request_code(phone: str) -> None` — normalizes the phone (reuses `bookings.normalize_phone`), enforces the rate limits (D-37: 3/hour, 5/day per phone, else `RateLimitError`), generates a 6-digit code, stores only `code_hash` + `expires_at` (+5 min), queues the SMS through `notifications.queue` (CR-1 D-28). Never returns or logs the plain code.
- `verify_code(phone: str, code: str) -> Customer` — loads the latest non-consumed code for the phone; wrong code increments `attempts` and raises `InvalidCodeError` (after 5 wrong attempts the code is invalidated, `TooManyAttemptsError`); expired raises `CodeExpiredError`. On success: marks `consumed_at`, `services.customers.get_or_create_customer`, sets `phone_verified_at`/`last_login_at`, links past guest bookings (D-38), logs the customer in.
- `customer_login_required` decorator; session key `customer_id`; 60-day session (D-36).
- Exceptions: `RateLimitError`, `InvalidCodeError`, `CodeExpiredError`, `TooManyAttemptsError`.

`services/customers.py` (CR-3)
- `get_or_create_customer(phone: str) -> Customer`
- `link_guest_bookings(customer: Customer) -> int` — sets `customer_id` on existing bookings with a matching phone and `customer_id IS NULL`; returns the count linked (D-38).
- `bookings_for_customer(customer_id: int) -> list[Booking]` — **only** that customer's rows, ordered newest first. The one query the "my bookings" page is allowed to use.
- `customers_with_counts() -> list[dict]` — for the admin customers list (name, phone, booking count, last login).

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
| GET, POST | `/admin/settings` | Owner settings (M7.4, M7.7): contact, address, hours, rules, confirmation note, booking window, tagline, about text, slot times, default price, price bands. `action=preview` re-renders with prices, saves nothing |
| POST | `/admin/settings/preview` | M7.7: price preview fragment for `admin_settings.js` (same resolver as the public site); saves nothing |
| POST | `/admin/settings/password` | M5.9: change the signed-in admin's password (current + new + confirm); signs out other sessions (D-49) |
| GET | `/admin/customers` | CR-3 (M13.6): customers list with booking counts and last login |
| GET, POST | `/account/login` | CR-3: enter phone number, request an OTP (rate-limited, D-37) |
| GET, POST | `/account/verify` | CR-3: enter the code; on success, logs the customer in (60-day session, D-36) |
| POST | `/account/logout` | CR-3 |
| GET | `/account/bookings` | CR-3: `customer_login_required`; only the signed-in customer's own bookings |
| GET, POST | `/account/profile` | CR-3: `customer_login_required`; edit name / optional email |

Guest booking (`/book`, `POST /book`) is **unchanged by CR-3** — it never checks for a customer session and never requires one.

WhatsApp link after booking: `https://wa.me/<whatsapp>?text=` + URL-encoded `"Hi, I requested a booking at TTURFZONE. Booking ID: TZ-XXXXXX, Date: ..., Time: ..."`.

### 5.5 Environment variables (`.env.example` lists names only)

`APP_ENV` (development|testing|production), `SECRET_KEY`, `DATABASE_URL` (production, CR-4: `mysql+pymysql://<user>:<password>@localhost/<database>?charset=utf8mb4`, password URL-encoded; `postgresql://...` still accepted), `TEST_DATABASE_URL` (optional, throwaway DB: a `mysql+pymysql://` URL runs `-m mariadb`, a `postgresql://` URL runs `-m postgres`).

CR-1 (names only; values only in the environment, never in git or .md):
`PAYMENTS_ENABLED` (default false), `PAYMENT_GATEWAY` (e.g. `bkash`), `HOLD_MINUTES` (default 10),
`BKASH_BASE_URL`, `BKASH_APP_KEY`, `BKASH_APP_SECRET`, `BKASH_USERNAME`, `BKASH_PASSWORD`,
`SMS_API_URL`, `SMS_API_KEY`, `SMS_SENDER_ID`,
`MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`,
`OWNER_ALERT_PHONE`, `OWNER_ALERT_EMAIL`.
Sandbox tests read `BKASH_*` from the environment and skip when unset (`@pytest.mark.sandbox`).

Engine options: `pool_pre_ping=True`, `pool_recycle=280` (kept for MariaDB: shared hosts often lower `wait_timeout` to a few minutes, 280 s stays under common values, and pre-ping catches anything else).

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
- [x] M1.3b Deployed to the real host through cPanel Terminal (no SSH). First attempt stopped at the database (host blocks outbound 5432, Neon unreachable) → CR-4 (MariaDB). Then: `git clone` in Terminal (cPanel Git Version Control rejects tokens in the clone URL; token stripped from the remote afterwards), `pip install -r requirements.txt`, `db-check` → `db upgrade` → `db-check` OK (round trip ~1 ms), `seed-settings`, `create-admin`, restart. Confirmed in production: Python 3.11.16, MariaDB 11.4.13, utf8mb4_unicode_ci, migration 13a53e9a5687, `UNIQUE KEY uq_active_slot_key` on the generated column, status CHECK constraint. Steps recorded in Appendix D. (2026-10-13)
- [x] M1.4 Dev wiring page `/dev/wiring`, `services/db_health.py`, `services/fake_data.py`, fake CLI commands (D-18).

Done when: `pytest -q` passes; host URL (temporary URL is fine) returns `ok` at `/healthz`; `db-check` succeeds on the host. This proves the risky parts early.

### Wiring check (developer, local, before hosting exists)

- [ ] W1 Unzip scaffold into repo, `pip install -r requirements-dev.txt`, `pytest -q` shows 42 passed, 4 skipped.
- [ ] W2 SQLite: copy `.env.example` to `.env`, set SECRET_KEY, `flask db upgrade`, `seed-settings`, `run --debug`, open `/dev/wiring`, press all three buttons.
- [x] W1 done (2026-09-11): `pytest -q` shows 42 passed, 4 skipped on Windows.
- [x] W2 done (2026-09-11): local SQLite, `/dev/wiring` works, all three buttons pressed.
- ~~W3 Neon project + branches~~ (CR-4: Neon unreachable from the host)
- ~~W4 Neon db-check / upgrade / seed / fake data~~ (CR-4)
- ~~W5 `pytest -m postgres` against Neon~~ (CR-4; still possible against any PostgreSQL if a move back is ever planned)
- ~~W6 `serve_like_passenger.py` against Neon~~ (CR-4)
- [x] W7 (CR-4) Local MariaDB 11.4.13 (portable ZIP, 127.0.0.1:3307, server default left at latin1 on purpose): `pytest -q -m mariadb` 11 passed; production-mode CLI rehearsal (`db-check` → missing tables, `db upgrade`, `db-check` → Database OK, `seed-settings`, `create-admin`, `db downgrade base`) clean. Making the unique index non-unique fails 5 tests, so the tests do catch it. (2026-10-13)

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

- [x] M3.1 `static/css/main.css`: design tokens (colour, type scale ~1.2, 4px spacing), buttons (primary/ghost/whatsapp, 44px touch, hover/press), cards + `.card--interactive`, `.ph` placeholder blocks (no stock images), header/nav, hero with scrim, slot grid states, footer, sticky mobile actions, `.wa-fab`, `.reveal` hooks, `prefers-reduced-motion` block. System fonts only. `base.html`: skip link, meta description, `{% block scripts %}`. Dev `/dev/wiring` styles ported. (2026-09-11) **Re-audited 2026-10-14** against the restated spec (dark base, green accent, 360/768/1280, hover + press + focus): added real press states (`.btn`, `.card--interactive`, date chips, gallery photos — before, `:active` only cancelled the hover lift, so a tap gave no feedback) and raised date chips to a 44px touch target. M3.2 and M3.3 re-audited the same day: no gaps beyond CR-5 (hero/gallery keep the real photos by developer decision; sticky bar + 76px body padding keep form buttons clear).
- [x] M3.2 `index.html` sections: hero, quick-booking placeholder grid (12 slot labels, static until M4.2), about, ~~facilities~~ (removed by CR-5), pricing, gallery (6 labelled placeholders), location (map embed placeholder + Get directions), reviews, Facebook, footer. All content via `TurfSettings.current_or_default()` (new: returns a transient TODO-placeholder row when unseeded). Partials: `partials/_macros.html` (photo/owner_text/camera), `partials/footer.html`. Every gap renders a visible `TODO(owner)` note naming its C-nn row. `tests/test_home_page.py` (7 tests): every section renders, no customer name/phone on `/` or `/api/availability`. 49 passed, 4 skipped. (2026-09-11)
- [x] M3.3 `partials/nav.html` (brand, desktop links >=900px, hamburger + full-screen menu below), `partials/sticky_actions.html` (WHATSAPP + BOOK NOW, hidden >=900px) + desktop WhatsApp FAB (only when a number is set), `static/js/main.js` (header `.at-top` over hero then solid; menu open/close/Esc/link-close, body scroll lock, focus return). Smooth scroll + header offset via CSS (`scroll-behavior`, `scroll-padding-top`), reduced-motion honoured. `tests/test_home_page.py` +2. 51 passed, 4 skipped. (2026-09-11) M3 complete.

Done when: layout works at 360px, 768px and 1280px, and every `TODO(owner)` maps to a Client inputs row.

### M4 Booking flow (Day 1, 14:30 to 18:00)

- [x] M4.1 `routes/api.py` `/api/availability` + `tests/test_availability_api.py`: bad date and missing date → 400; response is `Cache-Control: no-store`; slot shape is `time/label/state/price_bdt` only; no customer name or phone in the body; each state (available/pending/booked/blocked) shown. Booking-window rejection waits on M2.2. 54 passed, 4 skipped. (2026-09-11)
- [x] M4.2 `static/js/booking.js` + `partials/slot_picker.html`: server-rendered date chips for the booking window (Dhaka time, D-10), fetch `/api/availability` per date, 12 slot buttons with states, disabled slots use the real `disabled` attribute (not focusable/clickable), loading skeleton, "Try again" on fetch error, `.slot--selected` highlight, stale-response guard. Progressive enhancement: `[data-fallback]` (link to `/book` + WhatsApp) shows without JS. Homepage `#book` mounts it with a Continue button → `/book?date=&slot=`; `/book` mounts it with `picker_continue=false` and preselects from the query string. New `GET /book` route + `booking.html` (details form body is a placeholder note pending M4.3). `services/slots.py` gained `booking_window()` + `date_chip_label()` (M2.2 still owns `is_valid_slot`/`is_bookable`). Tests: `tests/test_slots.py` (3), `tests/test_public_routes.py` (7), `tests/test_availability_api.py` (from M4.1). 64 passed, 4 skipped. (2026-09-11)
- [x] M4.3 `booking.html` details form (name, phone) below the picker; hidden `date`/`slot` kept in step with the picker by `booking.js` (submit disabled until a slot is chosen). `POST /book` (CSRF via Flask-WTF): re-validates through `create_booking_request`; `BookingValidationError` → 400 re-render with per-field errors and the entered values kept; `SlotUnavailableError` → 409 re-render with "that slot was just taken" (picker reloads and shows it booked). (2026-09-11)
- [x] M4.4 `booking_success.html`: "Booking request received", booking ID, date, time (90 min), name, amber **Pending** pill, `confirm_time_text` (TODO note when unset), **Chat on WhatsApp** button (wa.me deep link with prefilled `Booking ID / Date / Time` text; TODO note when no number). Read once from `session["booking_request"]` (D-11); refresh → redirect home. (2026-09-11)
- [x] M4.5 `tests/test_public_routes.py` +10: happy path (302 → success, PENDING row, code on page), invalid phone / blank name re-render form (no row created), taken slot → 409 friendly error, past slot → 400 no row, missing slot → 400, `/book/success` with no session → home, one-time only (refresh redirects), WhatsApp link present/absent by settings. 112 passed, 4 skipped. Browser-verified the full flow at 375px. (2026-09-11)

Done when: the whole flow takes under a minute on a phone-sized viewport, and a duplicate attempt shows a friendly error.

- [x] M4.6 (CR-2) `create_booking_request` no longer inserts `PENDING` — confirms immediately (`PAYMENTS_ENABLED=false`, the only reachable state; `=true` raises `NotImplementedError` until M2.6/M10 land, D-41). Dropped the per-phone PENDING cap (`_settings()`/`TurfSettings` import removed, now dead). `booking_success.html`: "Booking confirmed!", green Confirmed pill, dropped the now-irrelevant `confirm_time_text` paragraph. Copy updated on `booking.html`, the footer disclaimer and the WhatsApp message: instant confirmation, no online payment yet, pay at the ground. `config.py` gained `PAYMENTS_ENABLED` (default False). `confirm_booking`/`reject_booking`/PENDING stay available for other paths (e.g. future M5.6 manual booking) — tested directly against a hand-built PENDING row. `tests/test_bookings.py`: -3 (dropped cap tests) +2 (confirmed-immediately, PAYMENTS_ENABLED guard); `tests/test_public_routes.py` updated. 143 passed, 4 skipped. Browser-verified: book → instant "Booking confirmed!" page. (2026-09-30)
- [x] M4.7 Slot grid with visible prices (extends M4.2). `services/pricing.py`: bands resolve to exactly one price per slot (D-47), weekend Fri+Sat (D-46), `turf_settings.default_price_bdt` fallback (migration `a4f7c2d9e1b3`, nullable). `/api/availability` adds `price_bdt` per slot via `prices_for_day`; still only time/label/state/price_bdt (tested). Slot cards: time + price only, 2 columns at 360px (4 at 640, 6 at 1024), time shrinks below 400px but never the price; states shown by the card's styling (available green outline, pending/booked dashed, blocked dotted, past faded; unavailable prices struck through; a screen-reader state word); `disabled` attribute on unavailable slots. Selection animates and the summary shows date, time range and "Total ৳…" before Continue. Homepage pricing section rebuilt as a price list from the same resolver ("Sunday to Thursday" / "Friday and Saturday", or one "Every day" block). `slots.slot_times()` added (constant for now, settings-driven in M7.7). `taka` template filter. `tests/test_pricing.py` (11), `tests/test_home_page.py` price-list test. 176 passed, 15 skipped; `pytest -m mariadb` 11 passed. Browser: 360px 2×160px cards, no overflow, summary "Today, 01:30 PM – 03:00 PM · Total ৳4,000"; 768px 4 cols; 1024px 6 cols; price list in two blocks. (2026-10-14)

### M5 Admin (Day 1, 18:00 to 22:00)

- [x] M5.1 `services/auth.py` (`verify_admin`, `login_admin`/`logout_admin` — `session.clear()` on both, `current_admin`, `safe_next`, `login_required`), `routes/admin.py` (GET/POST `/admin/login` generic error, `POST /admin/logout`, all pages `@login_required`, `?next=` limited to `/admin` paths), `templates/admin/base_admin.html` (own chrome, `noindex`), `login.html`, `static/css/admin.css`. Stub `dashboard`/`bookings`/`calendar` so the nav resolves. `tests/test_admin_routes.py` (15). 127 passed, 4 skipped. Browser-verified login → dashboard. (2026-09-11)
- [x] M5.2 `bookings.dashboard_summary(today)` + `bookings_for_day(day)`. Dashboard: 3 stat cards (bookings today / awaiting confirmation / confirmed this week), today's bookings table, next-7-days table, links to bookings + calendar. Customer name + `tel:` shown (admin only, behind login). `tests/test_admin_routes.py` +3. 130 passed, 4 skipped. (2026-09-11)
- [x] M5.3 `GET /admin/bookings?date=&status=` (exact-day + status filters, 300-row cap), table with `tel:` + `wa.me` links per customer (`_wa_number` 01→8801), status pill, code. `POST /admin/bookings/<id>/confirm` and `/reject` (CSRF, `login_required`, `InvalidTransitionError` → flash not crash, redirect back via safe `back` field). Reject/cancel has a JS confirm. `tests/test_admin_routes.py` +7. Sped the admin test fixture (cheap pbkdf2 hash). 137 passed, 4 skipped. (2026-09-11) (CR-2: "confirm" is transitional — goes with M4.6; reject/cancel stay.)
- [x] M5.4 `GET /admin/calendar?date=` — one day, 12 `.cal-slot` cards (state from `get_day_availability`, booking from `bookings_for_day`), prev/next day + date picker. Per slot: Block (reason field) for free future slots, Unblock for blocks, Confirm/Reject or Cancel for bookings, "Past" otherwise. `POST /admin/slots/block` (`SlotUnavailableError` → flash), `POST /admin/slots/<id>/unblock`. (2026-09-11)
- [x] M5.5 `tests/test_admin_routes.py` now 25 → covers logged-out redirect on every page + action, generic login failure, safe `next`, dashboard stats, list filters, confirm/reject, calendar 12 slots, block → public API sees `blocked` → unblock frees it, block on a taken slot flashes. 143 passed, 4 skipped. Browser-verified the whole admin flow. (2026-09-11)
- [ ] M5.6 (CR-1) `/admin/bookings/new`: manual booking for `phone` / `walk_in` customers (name, phone, optional email, date, slot; `source` set; no payment; goes straight to CONFIRMED or PENDING per owner choice). Uses `create_booking_request` so hold expiry + the unique index still apply.
- [ ] M5.7 (CR-1) `/admin/payments` list (filter by status/date) and `/admin/payments/<id>/refund` to record a refund done in the bKash dashboard (amount + note; sets `payments.status = REFUNDED`; optionally cancels the booking). No refund API call in v1.
- [ ] M5.8 (CR-3) `/admin/customers` list — name, phone, booking count, last login (built in M13.6, cross-referenced here).
- [x] M5.9 Admin password change + recovery. `/admin/settings` gains a separate "Change your password" form (`POST /admin/settings/password`: current, new, confirm; `autocomplete` current-password/new-password; never echoes values back). `services/auth.change_password`: current password required, new at least 12 characters and different from the current one, confirm must match; hashed with `Admin.set_password`; other sessions signed out (D-49), this one kept. `flask reset-admin-password --username <name>`: recovery from the server Terminal, prints a new 20-character password once, signs out every session. `tests/test_admin_routes.py` +5 (wrong current rejected, short + mismatched rejected, success: new password logs in and the old fails, other sessions signed out, login required), `tests/test_cli.py` +2 (reset works and changes the hash, unknown user). 194 passed, 15 skipped. Browser at 360px: form renders, no overflow. (2026-10-14)

Done when: the owner flow works end to end at phone width.

### M6 Day 1 wrap (22:00 to 23:30)

- [x] M6.1 Ran QA checklist §7 A–C locally at 360×740 (browser) + the automated suite. **No critical bugs found.** Fixed the checklist itself: struck the per-phone pending cap (removed by M4.6) and corrected "PENDING" → "Confirmed" on the success-page item. Confirmed as working: hero/sticky visible without scroll at 360px, no horizontal page overflow anywhere (admin tables scroll inside their own wrapper), full guest booking flow end to end, double-booking blocked client- and server-side, CSRF rejects an unsigned POST, admin confirm/login/logout/redirect-when-logged-out. Confirmed as **expected-not-built** (not bugs): map (C-07 pending), gallery lightbox (M7.2), CR-1/CR-3 admin screens (M5.6/M5.7/M13.6). (2026-09-30)
- [ ] M6.2 Push and deploy the current build to the host.
- [x] M6.3 Client follow-up message written as Appendix C (v2 signature + advance, hosting/domain, bKash documents, C-28 decision, all outstanding content items, CR-1/CR-3 inputs). Plan updated. (2026-10-01)

### M7 Content and polish (Day 2, 09:00 to 14:00)

- [x] M7.1 Real assets: logo and photos. Six real phone photos (WhatsApp, 1280×960, so no 1600px hero: never upscaled) → WebP 400/800/1280 via `scripts/build_images.py`, EXIF stripped; `img()` macro with `srcset`/`sizes`, `width`/`height`, `loading="lazy"` (hero `eager` + `fetchpriority=high`), alt text describing only what is visible. Hero = night floodlit photo; About = day + night; gallery = all six, lightbox loads the 1280 file. Logo: round emblem in the nav, PNG favicon + apple-touch-icon (SVG placeholder removed), 1200×630 `og:image` (logo + night photo), `twitter:card` → `summary_large_image`, JSON-LD gains `image` + `logo`. Supplied `hero.jpg` rejected (AI-generated per its C2PA metadata, shows a different pitch). Also removed the stale "name and phone step is added next (M4.3)" line from the homepage. `tests/test_home_page.py` +3. 164 passed, 15 skipped. Browser-checked at 375px and 1280px. Text, prices, reviews and map moved to M7.6. Deployed 2026-10-14: live homepage serves all six photos and the `og:image` (checked with curl). (2026-10-14) **Hero replaced by CR-7 (2026-10-14):** `hero.jpg` (illustration) instead of the night photo, which stays in the gallery.
- [x] M7.2 `gallery.js`: each gallery placeholder is now a `<button data-lightbox-item>` opening a shared overlay (`role="dialog"`, static markup, toggled like the nav menu) — keyboard (←/→/Esc), swipe (touchstart/end delta), click-out, focus moved to Close on open and back to the trigger on close. `reveal.js`: adds `.reveal-on` only when `!prefers-reduced-motion` and `IntersectionObserver` exists, then reveals each `.reveal` once and unobserves (content stays fully visible by default either way — progressive enhancement, same pattern as M3.2). `_macros.html` `photo()` gained `interactive=` (drops the div's own `role="img"`/`aria-label` when a wrapping button owns the accessible name). Success animation: a small stroke-drawn checkmark + a restrained card pop on `booking_success.html`, both plain CSS keyframes so the global `prefers-reduced-motion` rule already shortens them. Works on today's placeholders unchanged; same markup/JS carry over once M7.1 swaps in real `<img>` photos. `tests/test_home_page.py` +1, `tests/test_public_routes.py` +1 assert. 147 passed, 4 skipped. Browser-verified: lightbox opens/arrows/Esc/focus-return all correct, checkmark + card animate in on the success page. **Not independently re-verified live:** the scroll-triggered reveal itself — this session's browser pane repeatedly suspended rendering (`IntersectionObserver` callbacks and CSS transitions froze) while hidden/backgrounded, a known limitation of that tool, not evidence of a bug; the CSS rule and JS logic were confirmed correct by direct inspection (served stylesheet, matched selectors, standard IntersectionObserver pattern). (2026-09-30)
- [x] M7.3 `base.html`: canonical link, `og:type/site_name/title/description/url` (reusing the existing `title`/`description` blocks via `self.title()`/`self.description()`), `twitter:card`, SVG favicon (`static/icons/favicon.svg`, on-brand placeholder — a real mark comes with the logo, M7.1). `routes/public.py` `_local_business_json_ld()`: `LocalBusiness` JSON-LD on the homepage only, built field-by-field so a still-`TODO` value is omitted rather than emitted (never invented) — today that's just `name`, `url`, `sameAs` (the one real default, the Facebook link); `description`/`telephone`/`address` appear once the owner answers. **No `og-image.jpg`:** a placeholder share-card graphic would look broken in a real WhatsApp/Facebook preview, worse than no image — deferred to M7.1 when a real photo exists to crop. `tests/test_home_page.py` +3 (tags present, JSON-LD omits TODO fields, JSON-LD includes real ones). 146 passed, 4 skipped. Browser-verified: og/canonical/twitter tags render, JSON-LD parses, favicon renders. (2026-09-30)
- [x] M7.4 `/admin/settings` (D-23 scope): phone, WhatsApp, address, opening hours, booking rules, price bands. `services/settings.py` `save_owner_settings(form)` validates everything first and saves nothing on any error (`SettingsValidationError.errors`): phones via `normalize_phone` (WhatsApp stored as `8801…` for wa.me), opening hours ≤160 chars (VARCHAR limit Postgres enforces), up to 6 price bands — name, whole-taka price, days (all/weekday/weekend), ticked slots — fully blank rows dropped. Creates the `turf_settings` row if `seed-settings` never ran. Form never pre-fills seed `TODO(owner)` text; a failed save keeps what the owner typed. Admin nav gained Settings. `tests/test_admin_routes.py` +7. 154 passed, 4 skipped. Browser-verified at 375px: save → flash → homepage shows address, `tel:` link and the price band. (2026-09-30)
- [x] M7.5 `templates/errors/404.html` + `500.html` (500 touches no DB) + `@app.errorhandler` in `app.py`; `tests/test_error_pages.py` (no stack trace, working links). Accessibility pass: flash wrapped in `role="status" aria-live="polite"` (public + admin); booking form fields get `aria-invalid` + `aria-describedby` on error; slot grid `role="group" aria-label`; calendar block field/button `aria-label`; admin confirm/reject/cancel/block buttons get contextual `aria-label` (customer + slot); admin nav `aria-current="page"`; heading order fixed (footer `h4`→`h3` + `sr-only` `h2`), verified no skips on `/`, `/book`, admin. Contrast checked (all text ≥ 5:1 on the dark ground, muted/links ≥ 7:1). Global `:focus-visible` ring + `prefers-reduced-motion` already in place. Real `<img alt>` still to come with M7.1. 145 passed, 4 skipped. (2026-09-11)
- [ ] M7.6 Owner content still developer-entered (split from M7.1): reviews (C-18), map embed + directions link (C-07). ~~Facilities (C-16)~~ (CR-5). About text + tagline moved to the owner's settings page by CR-6 (M7.7). Prices, address, hours, phone and WhatsApp are owner-editable in `/admin/settings`. Waiting on the owner.
- [x] M7.7 (CR-6) `/admin/settings` extended (M7.4 kept): tagline, about text (≤1500), booking window (1–60 days), confirmation-page note (`confirm_time_text`, now shown on `/book/success`), the 12 slot start times (`type=time`, in order, ≥90 min apart; refused with booking codes if upcoming PENDING/CONFIRMED/BLOCKED rows sit at a removed time, D-48), required default price, up to 10 price bands. `static/js/admin_settings.js`: add / remove / move up / move down (renumbers fields, keeps focus), checkbox labels follow the slot times being typed, debounced live preview via `POST /admin/settings/preview`; without JS one blank band row and a "Preview prices" button. Preview table (`admin/_price_preview.html`): every slot × Sunday–Thursday / Friday–Saturday with the band name, "default" highlighted, "No price" in red, plus a count message. Dashboard warns when slots have no price or use the default. `slots.slot_times()` now reads `turf_settings.slot_times` (migration `b7e3d1f04a2c`); admin calendar, fake data and booking validation follow it. Validation errors save nothing and keep what was typed. `tests/test_admin_routes.py` +11 (text/window/note save, bad window + missing default, slot-time change moves bands and the public grid, overlap rejected, blocked by an upcoming booking with its code shown, past booking doesn't block, band order kept, preview marks default/missing and saves nothing, no-JS preview, preview requires login, dashboard warning). 187 passed, 15 skipped; `pytest -m mariadb` 11 passed; stranding query + both migrations up/down checked on MariaDB 11.4. Browser at 360/768/desktop: no page overflow, slot times 2/4 columns, preview table scrolls inside its box; reorder/remove/price edit/slot retime all update the preview live. (2026-10-14)

Done when: Lighthouse mobile targets reached or noted (performance 85+, accessibility 90+; targets, not blockers).

### M8 Production deploy (Day 2, 14:00 to 17:00)

- [x] M8.1 Production env vars on the host (cPanel Python App): `APP_ENV=production`, `SECRET_KEY`, `DATABASE_URL` set at M1.3b (2026-10-13). **2026-10-15:** confirmed the production `SECRET_KEY` is not the value that leaked through `.env.example` git history (checked by its first characters in the cPanel UI, value never shared).
- [x] M8.2 `flask db upgrade`, `seed-settings`, `create-admin` on production. No test data left. (Done as part of M1.3b, 2026-10-13; no fake-data commands were run, they are not registered in production.)
- [x] M8.3 Force HTTPS, certificate on the root domain and www, secure cookies. Certificate valid on both and session cookie `Secure; HttpOnly; SameSite=Lax` (2026-10-14). **HTTPS redirect fixed 2026-10-15** with cPanel → Domains → Force HTTPS Redirect: from outside, `http://tturfzone.com/`, `http://www.tturfzone.com/`, deeper paths and query strings all return `301` to the same `https://` URL. (A `curl` run from the server's own Terminal still showed 200, most likely run before the toggle took effect or via an internal route; external visitors are what matter.)
- [x] M8.4 Backups policy. **Host (2026-10-15, support answer):** JetBackup in cPanel keeps daily, weekly and monthly backups of the databases and home directory for about one month, and we can restore them ourselves from cPanel → JetBackup. Plus our own nightly dump (M8.8). Where JetBackup stores them (same server or not) was not stated. Still to do at handover: one manual `mysqldump` + restore steps in the handover notes (M9.4).
- [ ] M8.5 (CR-1) cPanel cron: three entries, once a minute — `flask jobs-expire-holds`, `flask jobs-send-notifications`, `flask jobs-send-reminders`. Confirm they run and log. **Cannot be added until M11 builds the job commands** (Known issues).
- [ ] M8.6 (CR-1) Email: create the SMTP mailbox; set SPF and DKIM DNS records; send one test email and check it is not spam-filed.
- [ ] M8.7 (CR-1) Set the new environment variables (§5.5). Launch with `PAYMENTS_ENABLED=false`. bKash + SMS creds stay as sandbox/empty until M12.
- [ ] M8.8 (CR-4) **Required before launch:** nightly `mysqldump` cron in cPanel (`--single-transaction --default-character-set=utf8mb4`, gzipped, keep the last 14, stored outside `public_html`). Credentials come from `~/.my.cnf` (chmod 600), never from the command line. Restore one dump into a scratch database to prove it works. Copy a dump off the server weekly. **Progress 2026-10-13:** daily 03:00 mysqldump cron with 14-day retention, credentials from `~/.my.cnf` (chmod 600, built from the stored connection string). Still to do: test one restore into a scratch database, and an off-server copy (Known issues). **2026-10-14:** the backup command is verified (real dump produced); exact cron line in Appendix D. Still open: one restore test and the off-server copy. **2026-10-15:** nightly job now runs `~/bin/tturf-backup.sh` (`set -euo pipefail`, writes to `.tmp`, checks it with `gzip -t`, only then renames it and prunes files older than 14 days; a failed dump stops before deleting anything). Cron command `/bin/bash /home/tturfzo1/bin/tturf-backup.sh > /dev/null`, so only errors reach the cron email. Test run OK. Still open: restore test into a scratch database; an independent copy outside the hosting provider (JetBackup is the provider's, so it doesn't cover losing the hosting account). **Restore test passed 2026-10-15:** `tturfzone-2026-10-14.sql.gz` restored into a scratch database `tturfzo1_restoretest`; row counts match live (admins 1, bookings 0, turf_settings 1, alembic_version 1) and the restored `bookings` table keeps the `STORED` `active_slot_key` + `uq_active_slot_key`, migration `b7e3d1f04a2c` and `utf8mb4_unicode_ci` (Appendix D, D15). Still open: an independent copy outside the hosting provider; confirm the first nightly run of the new script produced a new file.
- [x] M8.9 `/healthz` keep-alive cron every 5 minutes so the idle Passenger app is not put to sleep (a cold start would slow the first visitor from Facebook). `/healthz` touches no database (D-12), so this costs nothing. Cron line in Appendix D. (2026-10-13; `/healthz` → `ok` verified 2026-10-14)

Done when: `https://<domain>` loads, http redirects to https, admin login works on production, cron entries run, a test email arrives.

### M9 QA and handover (Day 2, 17:00 to 21:00)

- [ ] M9.1 Full QA checklist on a real Android phone, an iPhone if available, and desktop.
- [ ] M9.2 Production duplicate-booking test: two phones submit the same slot at the same moment; one succeeds. Delete test rows.
- [ ] M9.3 Owner training: 10-minute screen recording in Bangla (log in, confirm, reject, cancel, block, settings, **change the admin password**).
- [ ] M9.4 Handover pack delivered privately: accounts list, credentials, renewal dates and prices, how to request changes, support terms.
- [ ] M9.5 Set the Facebook page action button to the website booking page; add the site to Google Business Profile if one exists.
- [ ] M9.6 Tag `v1.0.0`; final plan update.
- [ ] M9.7 Transfer the GitHub repo to the owner's account and re-add the developer as a collaborator.
- [ ] M9.8 (CR-1) Owner training covers: manual booking (phone/walk-in), recording a refund, reading the payments list, topping up SMS balance. Handover pack (M9.4) lists the bKash, SMS and email accounts.
- [ ] M9.9 (CR-3) Owner training covers: reading the customers list, that accounts are optional and customers can always still book as a guest, that there are no customer passwords to reset (OTP only), and that OTP codes add to the SMS bill.

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

### M13 Customer accounts (CR-3)

Blocked from starting by: client sign-off + advance payment on the client summary v2 (D-40). SMS sending depends on the notifications outbox existing (CR-1 M11) — build M11 first.

- [ ] M13.1 `models/customer.py` (Customer), `models/login_code.py` (LoginCode) + migration; `bookings.customer_id` nullable FK + migration.
- [ ] M13.2 `services/otp.py` `request_code`: rate limiting (3/hour, 5/day per phone, D-37), 6-digit code generation, `code_hash` only (D-39), queues the SMS through the notifications outbox.
- [ ] M13.3 `services/otp.py` `verify_code`: 5-minute expiry, 5 wrong attempts then invalidate (D-37), creates/updates the Customer on success, `customer_login_required` decorator, session key `customer_id`, 60-day session (D-36).
- [ ] M13.4 `services/customers.py`: `get_or_create_customer`, `link_guest_bookings` (D-38), `bookings_for_customer`, `customers_with_counts`.
- [ ] M13.5 `routes/account.py`: `/account/login`, `/account/verify`, `/account/logout`, `/account/bookings` (only the signed-in customer's own rows), `/account/profile`. Confirm the guest `/book` flow is untouched — no session check anywhere in it.
- [ ] M13.6 `/admin/customers`: list with phone, name, booking count, last login (M5.8 cross-reference); link from the admin nav.
- [ ] M13.7 Tests: `tests/test_otp.py` (rate limits, expiry, wrong-attempt lockout, code never stored/logged in plain text), `tests/test_account_routes.py` (a customer never sees another customer's bookings, guest booking still works with no session, past guest bookings link on signup), `tests/test_admin_routes.py` additions for `/admin/customers`.

Done when: a customer can sign in with just a phone number and an SMS code, sees only their own bookings, guest booking is completely unaffected, and a burst of OTP requests is rate-limited.

### M12 Live payments (CR-1)

Blocked by: approved bKash merchant account in the owner's name (C-21).

- [ ] M12.1 Put live `BKASH_*` and `SMS_API_*` credentials in the production environment.
- [ ] M12.2 One real small payment end to end on production; confirm booking auto-confirms and SMS + email arrive.
- [ ] M12.3 One real refund in the bKash dashboard; record it in `/admin/payments`.
- [ ] M12.4 Set `PAYMENTS_ENABLED=true`. Watch the first day (payments list, notification `FAILED` rows, cron logs).
- [ ] M12.5 Register the branded `TTURFZONE` SMS sender; switch `SMS_SENDER_ID` when approved.

Done when: a real customer can pay and get an auto-confirmed booking with notifications, and one real refund has been recorded.

### Execution order (CR-1, CR-3)

M3 → M4.2 → M2.2, M2.3, M2.6, M2.7 → M4.3–M4.5 → M5 (incl. M5.6, M5.7, M5.8) → M10 → M11 → M13 → M6 / M7 → M8 → M9 → M12.

## 7. QA checklist

**A. Public site (phone first)**
- [x] Hero, BOOK NOW and WhatsApp visible without scrolling on a 360px screen (2026-09-30, 360×740)
- [x] Sticky mobile bar stays visible and doesn't cover form buttons (2026-09-30)
- [x] All sections show real or clearly marked placeholder content; no invented claims (2026-09-30)
- [ ] Map loads; GET DIRECTIONS opens Google Maps — not testable yet, `map_embed_url`/`map_link` are still TODO (C-07)
- [x] Gallery lightbox opens, swipes, closes (M7.2, 2026-09-30) — works on today's placeholder photos; unchanged once real `<img>`s land at M7.1
- [x] Facebook and WhatsApp links open the right page/number (2026-09-30: Facebook is the real default; WhatsApp correctly renders disabled/TODO pending C-06)

**B. Booking rules**
- [x] Past slots today show as unavailable (2026-09-30)
- [x] Dates outside the booking window can't be chosen, and the API rejects them (2026-09-30)
- [x] Invalid phone numbers rejected with a clear message (2026-09-30)
- [x] Booking a CONFIRMED or BLOCKED slot fails on the server (2026-09-30)
- [x] Rejected or cancelled slot becomes available again (2026-09-30)
- ~~Pending cap per phone works~~ — dropped by M4.6/CR-2, there is no manual PENDING step to cap. Backlog has a per-phone/IP rate limit instead, only if abuse appears.
- [x] Success page shows booking ID and **Confirmed** (was PENDING, changed by M4.6); refresh doesn't create a second booking (2026-09-30)
- [x] (M4.7) Every slot card shows its time and price together; 2 columns at 360px; price never shrinks (2026-10-14)
- [x] (M4.7) Weekend (Fri/Sat) and weekday prices resolve per D-47, including the default-price fallback (tests)
- [x] (M4.7) Unavailable slots are not selectable and are distinguishable without colour (dashed/dotted border, struck price, screen-reader state) (2026-10-14)
- [x] (M4.7) Selecting a slot shows the time range and total before Continue (2026-10-14)

**C. Admin**
- [x] Every `/admin` page redirects to login when logged out (covered by tests + 2026-09-30 spot check)
- [x] Wrong password shows a generic error (tests)
- [x] Confirm, reject, cancel, block and unblock update the public grid immediately (2026-09-30: confirm re-verified live; the rest already browser-verified at M5)
- [x] Filters by date and status work (tests)
- [x] Usable at phone width (2026-09-30, 360px: bookings table scrolls inside its own `.admin-table--scroll` wrapper, page itself never scrolls horizontally)
- [x] (M7.7) Settings pages and the preview endpoint require login (tests)
- [x] (M7.7) A slot-time change is refused while upcoming bookings/blocks sit at a removed time, naming them; past bookings don't block it (tests)
- [x] (M7.7) Price preview shows every slot for both day types and flags default / missing prices before saving (tests + browser)
- [x] (M5.9) Password change needs the current password, rejects short/mismatched new passwords, and signs out other sessions (tests)
- [ ] (CR-1) Manual booking for phone / walk-in works and respects the unique index — not built (M5.6)
- [ ] (CR-1) Payments list shows attempts; recording a refund sets REFUNDED and (optionally) frees the slot — not built (M5.7)
- [ ] (CR-3) Customers list shows booking counts and last login — not built (M13.6)

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

**C3. Customer accounts (CR-3)**
- [ ] Guest booking works end to end with no account, before and after CR-3 ships
- [ ] OTP expires 5 minutes after it is requested
- [ ] Wrong code attempts are capped at 5, then the code is invalidated
- [ ] Rate limit blocks a 4th code request within an hour and a 6th within a day, for the same phone
- [ ] A signed-in customer sees only their own bookings, never another customer's (try guessing another booking's id/url)
- [ ] Past guest bookings (matching phone) link to the account automatically on signup
- [ ] No plain OTP code appears anywhere in logs, the database, or an error message

**D. Security**
- [ ] No secrets in the repo (`git grep -i "password\|secret\|postgres://\|app_key\|api_key"` shows only names/placeholders)
- [ ] CSRF token required on all POST forms in production config
- [x] `/api/availability` contains no customer data (production 2026-10-14: 12 slots, keys `time/label/state/price_bdt` only)
- [x] Session cookie has Secure, HttpOnly, SameSite in production (2026-10-14: `Secure; HttpOnly; Path=/; SameSite=Lax` on `/admin/login`)
- [ ] (CR-1) A booking is only marked paid after a server-to-server gateway query that matches amount + `merchant_invoice`; redirect/query params are never trusted
- [ ] (CR-1) Payment callback is idempotent
- [ ] (CR-1) Gateway / SMS / SMTP credentials only in env; unit tests use fakes; sandbox tests skip without creds

**E. Production**
- [x] HTTPS on root and www; http redirects (2026-10-15: valid certificates; every `http://` URL returns 301 to its `https://` twin, checked from outside)
- [x] Security headers on production: X-Content-Type-Options, X-Frame-Options, Referrer-Policy (on `/healthz`, 2026-10-14)
- [x] `/dev/wiring` returns 404 in production: dev tools are off (2026-10-14)
- [x] `/healthz` returns `ok` and `/admin/login` loads in production (2026-10-14)
- [x] Production DB connected; migrations applied (MariaDB 11.4.13, 13a53e9a5687, 2026-10-13)
- [ ] Duplicate-booking test done on production (M9.2)
- [x] 404 page shows for unknown URLs; no debug tracebacks (production 2026-10-14: unknown URL → 404; `DEBUG` is off in `ProductionConfig`)

**F. Database engine (CR-4, MariaDB)**
- [x] `pytest -q -m mariadb` passes on MariaDB 11.4 (local 11.4.13, 2026-10-13)
- [x] 10 threads race for one slot: exactly 1 succeeds, 9 get `SlotUnavailableError` (2026-10-13)
- [x] `uq_active_slot_key` is a unique index on the STORED generated column `active_slot_key` with the expected CASE expression; no WHERE-less `uq_active_slot` on MariaDB (2026-10-13)
- [x] REJECTED frees the slot; PENDING, CONFIRMED and BLOCKED each hold it; several REJECTED rows can share a slot (2026-10-13)
- [x] A duplicate `booking_code` is a plain IntegrityError, not "slot taken" (2026-10-13)
- [x] Bangla round-trips through VARCHAR, TEXT and JSON; all tables utf8mb4_unicode_ci; `slot_time` comes back as a `time` (2026-10-13)
- [x] Migrations upgrade and downgrade cleanly on MariaDB (2026-10-13)
- [x] On production: `uq_active_slot_key` on the generated column and the status CHECK constraint are in place (M1.3b, 2026-10-13)
- [ ] Nightly mysqldump runs and one restore was tested (M8.8) — **restore tested and passing (2026-10-15)**; still to confirm one nightly run of `tturf-backup.sh` (a new dated file in `~/backups`)

## 8. Handover checklist

- [ ] Owner can log in to the admin on their own phone
- [ ] Owner changed the developer-generated admin password from Settings → "Change your password" on their own phone (M5.9); the developer no longer knows it
- [ ] Developer (and whoever keeps the hosting login) knows the recovery command for a lost password: `tz flask --app app reset-admin-password --username <name>` in cPanel Terminal (Appendix D, D14); it signs out every session
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
| C-12 | Logo, highest resolution (SVG/PNG) | D1-PM | **Received 2026-10-14** | 1024px JPEG on a dark background (no SVG/transparent version). Used as the cropped round emblem, favicon and share image (M7.1). An SVG or transparent PNG would still be sharper. |
| C-13 | 10 to 15 original photos from phone/camera: day, night under lights, wide field, facilities | D1-PM | **Partly received 2026-10-14** | 6 real photos (3 day, 3 night), WhatsApp-compressed to 1280px. Still wanted: the uncompressed originals (sharper hero on large screens), facilities (changing room, parking…), players in action. A supplied AI-generated aerial image was not used (D-45). |
| C-14 | Optional 10 to 20 second video | D1-PM | Pending | |
| C-15 | Opening hours and days | D1-AM | Pending | |
| C-16 | ~~Facilities that actually exist~~ | D1-PM | **Obsolete (CR-5)** | Facilities section removed from the site; ask again only if it comes back |
| C-31 | Which days count as the weekend for weekend prices? | Before prices are set | **Assumed Friday + Saturday** (Bangladesh's official weekend, D-46) | Confirm with the owner; it changes which price a Friday/Saturday slot gets |
| C-17 | Owner-approved description, 2 to 4 sentences | D1-PM | Pending | |
| C-18 | Real reviews and permission to show names | D1-PM | Pending | |
| C-19 | Confirm Facebook URL; other social links | D1-PM | Pending | |
| C-20 | Sports offered and turf format/size | D1-PM | Pending | Listing says 6-a-side futsal |
| C-21 | bKash merchant documents: trade licence, TIN, business bank account, NID | Before M12 | Pending | CR-1. Blocks live payments (M12). Sandbox build (M10) does not need these |
| C-22 | Full payment up front, or an advance percentage? | Before M10 | **Answered (CR-2): Tk 500 flat advance**, balance on site | Fills a fixed `advance_bdt = 500` |
| C-28 | Before bKash is live (M10), should the public booking form auto-confirm for free (cash on site), or stay closed until the advance works? | Before launch | **Implemented as "free" (D-41), developer default — client confirmation still wanted** | CR-2. Drives `PAYMENTS_ENABLED=false` behaviour |
| C-23 | Cancellation and refund rules text (who can cancel, when, how much back) | Before M10 | Pending | CR-1. Shown on the site and used for refund decisions |
| C-24 | Hold length in minutes (default 10) and reminder timing (default 2 hours before) | Before M10 | Pending | CR-1. `HOLD_MINUTES`, `reminder_hours_before` |
| C-25 | Owner alert phone (SMS) and owner alert email | Before M11 | Pending | CR-1. `OWNER_ALERT_PHONE`, `OWNER_ALERT_EMAIL` |
| C-26 | SMS provider preference / budget (or let developer choose) | Before M11 | Pending | CR-1. Non-masking first |
| C-27 | Written agreement to the new development price and the new owner running costs (bKash fees, SMS) | Before M10 start | Pending | CR-1. Blocks M10. Reissued client summary handled by the developer (.docx outside the repo) |
| C-29 | Is 60 days an OK length for a customer's login session, or does the owner want something shorter/longer? | Before M13 | Pending | CR-3. `D-36`. Planned default: 60 days |
| C-30 | Confirm an account is never required to book — guest booking always stays available | Before M13 | Pending | CR-3. Planned answer: **never required** (D-35) |

## 10. Change requests

| ID | Date | Request | Type (add/remove/modify) | Impact (time, scope, price) | Affected tasks | Status |
|---|---|---|---|---|---|---|
| CR-7 | 2026-10-14 | **Use `assets_raw/hero.jpg` as the hero picture.** Developer's request, reversing the M7.1 choice of the real night photo. The image is AI-generated (Google C2PA `trainedAlgorithmicMedia`) and shows a full-size aerial pitch, not TTURFZONE's netted futsal cage, so its alt text reads "Illustration: aerial view of a football pitch at sunset". About, gallery and the WhatsApp/Facebook share image keep the real photos. Re-encoding to WebP drops the file's C2PA provenance data along with all other metadata (the build script strips metadata from every image). | modify | **Time:** under an hour. **Scope:** `scripts/build_images.py` (hero output 800/1280/1920), `routes/public.py` `HERO`, `img()` macro takes per-image folder/widths/size, tests. **Price:** none. **Risk:** customers may expect the pitch shown in the hero (Risks). | D-45, M7.1, CLAUDE.md photo rule, §12 | Done 2026-10-14 (local; deploy with the next pull) |
| CR-6 | 2026-10-14 | **The owner can edit a little more from the admin.** Previously (D-23): prices, hours, contact details, booking rules. Now also: the **12 slot start times**, the **about text** and the **tagline** (plus the confirmation-page note and booking window, already columns). A slot-time change is refused, with an explanation, if upcoming bookings or blocks sit at a time being removed. Images, page layout and design remain developer-only; hero and gallery image upload stays in the Backlog as paid phase 2. *The developer's message labelled this "CR-5"; recorded as CR-6 because CR-5 is the Facilities removal.* | modify | **Time:** minor, under half a day. **Scope:** settings form + validation, slot times read from `turf_settings` instead of a constant (D-09 superseded), orphan check, tests. **Price:** none proposed (minor). | D-09, D-23, new M7.7, §5.2 turf_settings, §5.3 slots | Recorded 2026-10-14; built as M7.7 |
| CR-5 | 2026-10-14 | **Remove the Facilities section from the homepage.** Gone from the page, the nav (desktop + mobile menu) and the `turf_settings` seed. The `facilities` JSON column stays in the model, unused, so bringing the section back needs no migration. *The developer's message labelled this "CR-4", but CR-4 already exists (MariaDB), so it is recorded as CR-5.* | remove | **Time:** under an hour. **Scope:** template, nav, CSS, seed, tests, plan. **Price:** none. C-16 becomes obsolete. | M3.2, M7.6, D-13, §5.2 turf_settings, C-16, Appendix C | Done 2026-10-14 |
| CR-4 | 2026-10-13 | **Production database: PostgreSQL (Neon) → MariaDB on the host.** The host (Cyber Developer BD, shared cPanel, server srv2) blocks outbound TCP 5432. Checked from the server: "Connection refused" on every Neon IPv4 address and "Network is unreachable" on IPv6, while outbound HTTPS works (HTTP/2 200 from google.com). Changing hosting is not an option; the host's MariaDB 11.4 on localhost needs no outbound connection. Overrides brief §8 (PostgreSQL) for production; PostgreSQL support stays in the code. *The developer's message labelled this "CR-3", but CR-3 already exists (customer accounts), so it is recorded as CR-4.* | modify | **Time:** about half a day (done 2026-10-13). **Scope:** driver, URL handling, the double-booking rule on MariaDB (generated column, D-42), migration, tests, docs; no change to app behaviour. **Price:** none proposed (an infrastructure fix, not a feature); developer's call. **Owner costs:** none (MariaDB comes with the hosting), but backups are now ours to run (M8.8). | D-01, D-02, D-03, D-08, D-12, D-21, D-42…D-44; §2; §4; §5.1, §5.2, §5.5; W3–W7; M1.3b; M8.4, M8.8; §7 F; §12; §13; Appendix D | Done and tested locally 2026-10-13 (MariaDB 11.4.13). **Not deployed**: M1.3b resumes with Appendix D. |
| CR-3 | 2026-09-16 | **Customer accounts.** Customers can create an account (phone number + a one-time SMS code, no password) and see their booking history. Guest booking without an account stays available and is never blocked. A verified phone number on a booking reduces fake bookings. Sessions last 60 days. The OTP goes through the same notification outbox as other SMS (~Tk 0.35/code). | add | **Time:** +1 day (6 days total). **Price:** Tk 30,000 development (reissued client summary v2, see D-40). **Owner costs:** SMS cost rises (OTP codes on top of booking notifications); no extra hosting or database cost. | Global constraints §2; §5 (models, services, routes); new M13; M5 (admin customers list); M9 (handover); §7 QA; §9 client inputs; §11 backlog; §12 risks; D-34…D-40 | Recorded 2026-09-16. Sent to client as version 2 of the client summary (Tk 30,000, outside the repo), **not yet signed**. M13 (and M10) blocked until v2 is signed and the advance paid. Frontend work continues. |
| CR-2 | 2026-09-11 | **No manual confirmation at all.** The website decides every booking by itself: an empty slot can be booked, a taken slot cannot — the admin never has to intervene for a normal booking (but keeps full override: cancel, block, manual booking, refunds). Confirmation is by a **Tk 500 bKash advance** (bKash wired later — CR-1 M10); the balance is paid on site after the slot. Answers C-22 (advance = Tk 500 flat, not a percentage, not full payment). | modify | **Removes** the manual `PENDING → owner confirms` flow and CR-1's `PAYMENTS_ENABLED=false` "manual mode". `create_booking_request` will produce `CONFIRMED` (free/interim) or `PENDING_PAYMENT` (bKash), never `PENDING`. **Interim (before M10):** needs a call — auto-confirm free (cash on site) as a temporary launch mode, or keep the public booking form closed until bKash is live (open question, tracked as C-28). **Time:** small (mostly deletion) once M2.6/M10 land. **Price:** inside CR-1's repricing, no extra. | D-05 (superseded), D-24, CR-1 M2.6 / M4.3 / M4.4 / M10, C-22 (answered), new M4.6, M5.3 (confirm action now transitional) | Recorded 2026-09-11. Per developer: **M5 is built now against the current PENDING model and adapted when M2.6 lands** ("M5 now, adapt after"). |
| CR-1 | 2026-09-11 | Make the website self-sufficient: online payment (bKash direct gateway, server-verified), automatic confirmation, SMS + email notifications, slot holds, scheduled jobs, admin manual bookings + payments/refunds. Overrides brief §2 ("no online payment"); removes "online payments/bKash" and "SMS gateway" from brief §15 exclusions. Still excluded: customer accounts, automated WhatsApp API, multiple branches, tournaments, coupons, complex analytics, native app, AI chatbot, large CMS. | add / modify | **Time:** +2–3 dev days (4–5 total). **Price:** development must be repriced — developer estimate ~Tk 25,000 at the original daily rate; **superseded by the combined CR-1+CR-3 client summary v2, Tk 30,000 (D-40), not yet agreed**; D-15…D-17 superseded. **Owner costs:** new running costs (bKash 1.5–2% per txn, SMS ~Tk 0.25–0.40 each, possible masking-sender registration). **Blockers:** live payments need an approved bKash merchant account in the owner's name (trade licence, TIN, business bank account, NID, live URL; ~1–3 weeks). | Global constraints §2; D-05, D-11, D-15–D-17; §5 (models, services, routes, env); new M2.6, M2.7, M5.6, M5.7, M10, M11, M12; M8; §7, §8, §9, §11, §12 | Recorded 2026-09-11. Repricing + owner running-cost agreement pending (blocks M10 start). Merchant approval pending (blocks M12). Frontend (M3, M4.2) continues unaffected. |

## 11. Backlog (after MVP)

- ~~Online payment (bKash/Nagad/SSLCommerz) with advance deposit~~ — now in scope (CR-1)
- ~~Automatic confirmations (SMS or WhatsApp Business API)~~ — SMS/email now in scope (CR-1); WhatsApp API stays below
- WhatsApp Business API for confirmations and reminders (CR-1: deferred)
- Automatic refunds via the bKash refund API (CR-1: v1 records manual refunds only)
- Nagad and card payments via an aggregator (SSLCommerz / aamarPay) (CR-1)
- SMS low-balance alert to the owner (CR-1)
- Bangla notification templates (CR-1: English first)
- Per-phone / per-IP booking rate limit (replaces the dropped D-05 pending cap; only if spam appears — CR-2)
- Optional password login for customers, alongside OTP (CR-3: OTP-only for now, D-34)
- Customer self-cancel from the account page (CR-3; distinct from the existing "self-cancel with a code" item below, which needs no account)
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
| ~~Neon free compute hours used up~~ | Obsolete: Neon is not used (CR-4) |
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
| (CR-3) SMS cost abuse through the OTP endpoint (someone hammers `/account/login` to run up the bill) | Rate limits enforced server-side: 3 codes/phone/hour, 5/day, 5 wrong attempts per code (D-37). |
| (CR-3) Customers drop off if account signup is ever forced or nagged | Guest booking is permanent and unconditional (D-35); accounts are offered, never required. |
| (CR-3) Client summary v2 not signed | M13 (and M10) do not start until it is signed and the advance is paid; frontend and non-CR-3 work continue meanwhile. |
| (CR-4) Engine differences: production is MariaDB, everyday tests run on SQLite, and the double-booking rule is built differently per engine (partial index vs generated column, D-42), so a bug in one won't show in the other | Run `pytest -q -m mariadb` (10-thread race + index-definition check) against MariaDB 11.4, not MySQL, before every deploy and after every model or migration change. The tests are proven to fail when the index is broken. SQLite is UX-only, never proof. |
| (CR-4) The host's MariaDB has no automatic backups we control (Neon had point-in-time restore) | M8.8: nightly mysqldump cron, a tested restore, and a weekly off-server copy. **Required before launch.** |
| (CR-4) A status-list change (CR-1's `PENDING_PAYMENT`) must update two definitions: the partial-index WHERE and the MariaDB generated-column expression | Called out in §5.2 and the CLAUDE.md gotchas; the MariaDB index-definition test asserts the status list, so it fails until both change. |
| (CR-7) The hero shows an AI-generated aerial pitch, not the real ground; a customer could expect a different, bigger field | Alt text labels it an illustration; the gallery and about section show the real ground right below. Swap back to a real photo (`HERO` in `routes/public.py`) once good owner photos arrive (C-13). |

## 13. Known issues

- (M5.9) Admin sessions created before the M5.9 deploy have no password fingerprint, so the owner is signed out once and must sign in again. Expected, harmless.

- (M7.7) The admin calendar shows the current 12 slot times. After a slot-time change, a **past** day's booking at an old time no longer appears in that day's calendar grid; it is still in the Bookings list. Upcoming bookings can't be stranded (D-48).
- (M7.7) The stranded-booking check and the save are not one locked transaction: a customer booking an about-to-be-removed time in the same second could still land. Very unlikely on one ground; the booking stays visible in the Bookings list.
- (M4.7/M7.7) Until the owner saves prices, every slot shows "On request" and the dashboard says 24 slot prices are not set. Production is in that state today (C-02).

- (M7.1 deploy) **Always restart after a `git pull`.** Right after the M7.1 pull the homepage returned 500 while `/book`, admin and the new static files were fine; after a restart it worked. Most likely the running Passenger process still had the old Python code while it loaded the new `index.html` (which needs the new `PHOTOS` context), so only the homepage broke. The update one-liner in Appendix D already ends with `touch tmp/restart.txt`; if the site still errors, use cPanel → Setup Python App → Restart.

- (M7.1) The photos are WhatsApp-compressed (1280×960), so the hero is at most 1280px wide and slightly soft on large desktop screens. Ask for the original camera files (C-13), drop them into `assets_raw/` under the same file names (or update `PHOTOS` in `scripts/build_images.py`), re-run the script, commit.
- (M7.1) Browsers also request `/favicon.ico` and get a 404. Harmless: every page links the PNG favicon.

- ~~(M8.3) Plain `http://` was served without a redirect~~ Fixed 2026-10-15 (Force HTTPS Redirect in cPanel; external check shows 301 everywhere).
- ~~(M8.8) The backup cron could fail silently (gzip's exit status hid a failed mysqldump, and the prune still ran)~~ Fixed 2026-10-15: `~/bin/tturf-backup.sh` uses `pipefail`, verifies the gzip, and prunes only after a good dump (Appendix D).

- (M1.3b) **Our nightly dumps live on the same server as the database.** Since 2026-10-15 we know the host also keeps JetBackup snapshots (daily/weekly/monthly, ~1 month, self-restore), which covers a server failure if they're stored elsewhere (not confirmed). Neither covers losing the hosting account itself, so a copy outside the provider (e.g. the owner's Google Drive, monthly at least) is still wanted before handover (M8.8).
- (M1.3b) The CR-1 jobs cron (`jobs-expire-holds`, `jobs-send-notifications`, `jobs-send-reminders`, M8.5) cannot be added until M11 builds those commands. Nothing needs it today: there are no holds or notifications yet.
- (M1.3b) The repo is private, so every `git pull` on the server needs a GitHub token. Use a fine-grained read-only token passed as a one-off header (Appendix D, D3); never leave it in the remote URL. cPanel Git Version Control can't be used because it rejects tokens in the clone URL.

- (CR-4) `.env.example` shipped a real-looking `SECRET_KEY` value from the scaffold commit (`6fc49b0`) until 2026-10-13; it is still in git history. If production's `SECRET_KEY` in the cPanel Python App settings was copied from it, generate a new one there and restart (it only logs the admin out).
- (CR-4) M1.3b's first attempt stopped at the database step: the host blocks outbound port 5432, so Neon cannot be reached. Resolved by moving production to the host's MariaDB; deployed 2026-10-13.
- (CR-4) `flask db-check` used to time the first `SELECT 1`, which includes the connection handshake (about 150 ms even to localhost on Windows). It now connects first and times a second query, so "Round trip" is the real query time.
- (CR-4) DateTime values come back naive on MariaDB/SQLite and aware on PostgreSQL (D-44). Harmless today because no code reads them.

- Admin's "Confirm" action and "Awaiting confirmation" dashboard stat are now vestigial for the guest flow (M4.6 ships bookings CONFIRMED already) — kept working for any row that is still PENDING by other means (e.g. the future M5.6 manual booking). Reject/cancel, block/unblock, filters and the dashboard are otherwise unchanged.
- Rejecting/cancelling a booking does not notify the customer (no SMS/email until CR-1 M11). The confirm dialog says so.
- No admin "add a phone/walk-in booking" screen yet (CR-1 M5.6).
- Accessibility (M7.5) covered structure/aria/contrast/focus. Real photos (M7.1) all have alt text describing what is visible (tested). A full screen-reader / Lighthouse run belongs in M9.1.
- ~~`price_bdt` in the availability API is `null` until pricing is wired~~ Resolved by M4.7. It is still `null` (shown as "On request") until the owner saves prices; production has no prices yet (C-02).
- WhatsApp buttons (hero, sticky bar) render disabled and the desktop WhatsApp FAB is hidden until the owner gives the number (C-06). `tel:` link in the footer likewise waits on C-06.
- Customer booking flow works end to end, auto-confirm mode (M4.6): `/book` picker + form → `POST /book` → `/book/success` (session, one-time), status CONFIRMED immediately. No online payment yet (CR-1 M10, gated). No email field yet (CR-1 M2.6).
- `/api/availability` reads `booking_window_days` from `turf_settings` on every request; when M7.4 lets the owner change it, in-flight pickers keep the old chips until reload (acceptable).
- The `/book` name/phone form has no client-side validation beyond `required`; the server (`create_booking_request`) is the gate. Good enough; nicer inline JS validation is polish (M7.5).
- (CR-1) The footer disclaimer, `/book` and the success page now say "confirmed instantly, no online payment yet" (M4.6) — correct while `PAYMENTS_ENABLED=false`. This copy must change again when M10 wires the Tk 500 advance and the flag can be `true`.
- (CR-1) No `payments` / `notifications` tables or new booking statuses yet — M2.6. All payment/notification tasks (M10–M12) are unstarted and gated (see CR-1 and Risks).
- (CR-3) No `customers` / `login_codes` tables, no `bookings.customer_id`, and no `/account/*` routes yet — all of M13 is unstarted and gated on the client signing v2 (D-40) and on M11 (notifications outbox) existing first.
- ~~(M7.3) No `og:image`; SVG favicon placeholder~~ Resolved by M7.1: real `og-image.jpg` (1200×630) and PNG favicon from the owner's logo.
- (M7.3) JSON-LD `address` is emitted as a plain string, not a structured `PostalAddress` (we only store one free-text address field); `openingHours` is intentionally omitted because the stored `opening_hours_text` is prose, not the structured day/time format schema.org expects — emitting it as-is would be invalid data.

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
| 2026-09-16 | Docs (Claude Code, Windows) | CR-3 recorded (customer accounts: phone + one-time SMS code, no passwords, guest booking always available, 60-day sessions, OTP through the shared outbox, rate-limited). Note: the developer's message labelled this "CR-2", but CR-2 already exists (no-manual-confirmation) — recorded as **CR-3** instead and flagged to the developer. Documentation only, no code/templates/migrations/tests touched. Updated CLAUDE.md (4 customer-account hard rules) and the plan: §1 budget (v2, Tk 30,000/6 days), §2 constraints (customer accounts back in scope, guest booking guaranteed), D-34…D-40 added (OTP not passwords, guest booking permanent, 60-day session, OTP rate limits, guest-booking linking, hashed codes, client summary v2), D-15/D-16/D-17/CR-1 status pointers updated to D-40, §5 file map / data model (`customers`, `login_codes`, `bookings.customer_id`) / service contracts (`services/otp.py`, `services/customers.py`) / routes (`/account/*`, `/admin/customers`), new M13 + execution-order update, M5.8 and M9.9 cross-references, §7 QA (C3 block), §9 client inputs (C-29, C-30), §11 backlog, §12 risks, §13 known issues. | Awaiting client signature on v2 (D-40) + advance; M13 and M10 blocked until then. Developer go-ahead needed before any further build task. |
| 2026-09-30 | Build (Claude Code, Windows) | M4.6 (CR-2): `create_booking_request` drops the manual `PENDING` path and confirms immediately (`PAYMENTS_ENABLED=false`, D-41 — the only state buildable today; `=true` raises `NotImplementedError` until M2.6/M10). Dropped the per-phone PENDING cap and its now-dead `_settings()`/`TurfSettings` import. `config.py` gained `PAYMENTS_ENABLED`. Updated copy on `booking.html`, `booking_success.html` (green Confirmed pill, no more `confirm_time_text`), the footer disclaimer and the WhatsApp message. `confirm_booking`/PENDING kept working for non-guest paths (tested directly). `tests/test_bookings.py` -3/+2, `tests/test_public_routes.py` updated. 143 passed, 4 skipped. Browser-verified: book → instant "Booking confirmed!". | C-28 needs the client's own sign-off on the D-41 default; next build pick per Resume here |
| 2026-09-30 | Build (Claude Code, Windows) | M7.3: `base.html` gained canonical link, OG (`type`/`site_name`/`title`/`description`/`url`), `twitter:card`, and an SVG favicon placeholder (`static/icons/favicon.svg`). `routes/public.py` `_local_business_json_ld()`: homepage `LocalBusiness` JSON-LD, field-by-field so a `TODO` value is omitted, never invented — today just `name`/`url`/`sameAs` (Facebook). Deliberately no `og-image.jpg` (a placeholder share-card graphic would look worse than none) or structured `openingHours` (stored text is prose, not schema.org's format) — both noted in Known issues. `tests/test_home_page.py` +3. 146 passed, 4 skipped. Browser-verified: tags + JSON-LD render correctly, favicon renders. | M6 / M7.1-M7.2 / M2.6 / M13 — see Resume here |
| 2026-09-30 | Build (Claude Code, Windows) | M6.1: local QA pass, §7 sections A-C at 360×740 in the browser plus the automated suite. No critical bugs. Verified: hero/sticky visible without scroll, no page-level horizontal overflow anywhere (admin tables scroll in their own wrapper), full guest booking flow, double-booking blocked (client + server), CSRF rejects an unsigned POST, admin login/logout/redirect/confirm. Confirmed expected-not-built: map (C-07), gallery lightbox (M7.2), CR-1/CR-3 admin screens. Fixed the checklist itself: struck the per-phone pending cap item (removed by M4.6) and corrected the success-page item from PENDING to Confirmed. 146 passed, 4 skipped, unchanged (docs + checklist only, no app code touched). | Developer pick: M2.6/M13 (needs v2 signed) / M6.2 deploy (needs hosting) / M7.1-M7.2 (needs owner assets) |
| 2026-09-30 | Build (Claude Code, Windows) | M7.2: `gallery.js` lightbox (each placeholder is a `<button data-lightbox-item>`, shared overlay dialog, keyboard/swipe/click-out, focus managed like the nav menu), `reveal.js` (adds `.reveal-on` only when motion isn't reduced and `IntersectionObserver` exists, reveals once per element), success-page checkmark + card pop (plain CSS keyframes, already covered by the global reduced-motion rule). `_macros.html` `photo()` gained `interactive=` for the lightbox-button case. None of this needed owner photos - same markup/JS carries over once M7.1 lands real `<img>`s. `tests/test_home_page.py` +1, `tests/test_public_routes.py` +1 assert. 147 passed, 4 skipped. Browser-verified: lightbox open/arrows/Esc/focus-return, success animation. Could not independently re-verify the scroll-triggered reveal live - this session's browser pane kept suspending rendering (IntersectionObserver/CSS transitions freeze) while hidden, a tool limitation; correctness confirmed by inspecting the served CSS and matched selectors instead. | M7.4 admin settings (recommended, no blocker) / M2.6 / M13 / M6.2 / M7.1 |
| 2026-09-30 | Build (Claude Code, Windows) | M7.4: `/admin/settings` + `services/settings.py` (validate-then-save, phones normalized, WhatsApp stored as 8801…, hours ≤160, up to 6 price bands with ticked slots, creates the settings row if missing). Seed TODO text never pre-fills the form; failed saves keep input. Admin nav: Settings. `tests/test_admin_routes.py` +7. 154 passed, 4 skipped. Browser-verified save → public site at 375px. | Blocked on the client: v2 signature (M2.6/M10/M11/M13), hosting (M6.2/M8), assets (M7.1) |
| 2026-10-01 | Build (Claude Code, Windows) | Visual pass at 768px and 1280px (every public + admin page: no page-level overflow, nav/sticky/FAB switch at 900px, grids correct). **Found and fixed two real bugs:** (1) `.lightbox` is `display:flex`, which beat the `hidden` attribute, so the closed lightbox overlay covered the whole homepage on every load since M7.2 — fixed at the root with a global `[hidden] { display:none !important }` (removed the now-redundant `.nav-menu[hidden]`); (2) nav/footer/sticky links (`#about`, `#pricing`, `#book`…) were dead on `/book` and `/book/success` — section links now `/#section`, "Book now" uses `book_href` (`#book` on the homepage, `/book` elsewhere) from the public context processor. Also: price card shows 12-hour labels ("All slots" when a band covers all 12); slot grid locked to 4 cols ≥640px and 6 ≥1024px so 12 slots fill even rows. M6.3: client follow-up message written as Appendix C. Tests +4 (CSS `[hidden]` guard, no dead `#` links on any public page, Book-now target, 12-hour price labels). 158 passed, 4 skipped. Lesson: tests that only check markup presence missed a visual-only bug — the lightbox was "present" and covering everything. | Send Appendix C to the client |
| 2026-10-13 | Build (Claude Code, Windows) | **CR-4 MariaDB support** (host blocks port 5432, Neon unreachable). PyMySQL replaces psycopg in production (psycopg → dev only); `normalize_database_url` accepts `mysql://`; utf8mb4 forced on every table (`MYSQL_TABLE_OPTIONS`). Double-booking on MariaDB = STORED generated column `active_slot_key` + unique `uq_active_slot_key` (D-42): hand-edited initial migration branches on dialect, `after_create` DDL for `create_all`, `Index.ddl_if` keeps the partial index off MariaDB, `env.py` hides the hand-written rule from autogenerate. `_is_slot_conflict` documents all three engines' messages. `pytest.ini` + `conftest.py`: `mariadb` marker; `TEST_DATABASE_URL`'s scheme picks the marker. New `tests/test_mariadb.py` (11): index definition (migration and create_all), 10-thread race, REJECTED frees / PENDING-CONFIRMED-BLOCKED hold, duplicate booking_code is not "slot taken", Bangla/JSON/time/UTC round-trip, utf8mb4 + lower-case tables, downgrade. Ran against a local MariaDB 11.4.13 (portable ZIP, latin1 server default on purpose): 11 passed; a non-unique index fails 5, so the tests are real. Production-mode CLI rehearsal clean. Also: `db-check` now times a warm query (it was timing the ~150 ms handshake); blanked a committed `SECRET_KEY` value in `.env.example` (Known issues). Found PyMySQL silently drops timezone offsets (D-44). SQLite suite 161 passed, 15 skipped. | Resume M1.3b with Appendix D, then M8.8 (mysqldump cron) |
| 2026-10-13 | Deploy (developer + Claude Code, docs only) | **M1.3b done: production live at https://tturfzone.com.** Cyber Developer BD cPanel (srv2), Python 3.11.16, Passenger, MariaDB 11.4.13 on localhost (~1 ms, utf8mb4_unicode_ci). Cloned with `git` in cPanel Terminal (cPanel Git Version Control rejects tokens in the URL; token stripped from the remote). Migration 13a53e9a5687 applied; `uq_active_slot_key` + status CHECK confirmed; settings seeded; admin created. Cron: daily 03:00 mysqldump (14-day retention, `~/.my.cnf`) and a 5-minute `/healthz` keep-alive. Known issues: backups on the same server; jobs cron waits on M11. M8.2 ticked, M8.9 added. Plan only, no code changed. | Off-server backup copy + restore test (M8.8), rest of the M8 checks; client inputs |
| 2026-10-14 | Verify (developer + Claude Code, docs only) | **Production verification.** Passing (developer on the server, re-checked with curl from outside): valid certificate on tturfzone.com and www, security headers, `/dev/wiring` 404, `/api/availability` 12 slots with no customer data, `/healthz` ok, `/admin/login` loads, session cookie Secure/HttpOnly/SameSite=Lax, unknown URL 404, test mysqldump produced a real dump. **Failing (found from outside):** plain `http://` on both hosts returns 200 with no redirect; M8.3 stays open. Exact cron lines + `\%F` escaping note in Appendix D. New Known issue: the backup pipeline masks mysqldump failures (`pipefail`). QA D/E items ticked; M8.4/M8.8 progress noted. Plan only, no code changed. | M8.3 Force HTTPS Redirect, M8.8 off-server copy + restore test; next build task M2.6 waits on the v2 signature |
| 2026-10-14 | Build (Claude Code, Windows) | **M7.1 real photos + logo.** `assets_raw/` (gitignored) → `scripts/build_images.py` (Pillow, dev-only, D-45) → WebP 400/800/1280 for six real photos (EXIF stripped), nav emblem, PNG favicon + apple-touch-icon, 1200×630 `og:image`. `routes/public.py` `PHOTOS` (order + alt text), `img()` macro (srcset/sizes, lazy, hero eager + high priority), hero/About/gallery switched to real photos, lightbox shows the 1280 file, `og:image` + `summary_large_image`, JSON-LD `image`/`logo`. **Did not use the supplied `hero.jpg`**: its C2PA metadata says AI-generated (Google) and it shows a different pitch; developer picked the real night photo. Removed a stale M4.3 note from the homepage. `tests/test_home_page.py` +3 (files at all widths, 4:3, no EXIF; alt text + lazy/eager; icons + og:image). 164 passed, 15 skipped. Browser: 375px hero/gallery/no overflow; 1280px lightbox opens the 1280 file, Esc closes; no console errors. Text content split out as M7.6. | Deploy (pull + restart); M8.3/M8.8; M7.6 + M2.6 wait on the client |
| 2026-10-14 | Deploy (developer + Claude Code, docs only) | **M7.1 deployed.** Pulled on the server with a new GitHub token. The homepage briefly returned 500 (only `/`; `/book`, admin and the new static files were fine) until the app was restarted, most likely a stale Passenger process running old code with the new template. Now live: `/` 200 with all six photos, `og:image` served, no placeholders left (checked with curl). Recorded the restart lesson in Known issues. Discussed a read-only GitHub deploy key over SSH port 443 so pulls need no token; not set up yet. Plan only, no code changed. | M8.3, M8.8, optional deploy key; M2.6/M7.6 wait on the client |
| 2026-10-14 | Build (Claude Code, Windows) | **CR-5: Facilities section removed** (recorded as CR-5, developer called it CR-4). Section, both nav links, `.facility` CSS and the `facilities` seed key removed; column kept, unused. `tests/test_home_page.py`: section list updated, new `test_no_facilities_section_or_link`. 165 passed, 15 skipped. | CR-6 record, then M3.1–M3.3 audit, M4.7 slot prices, M7.7 admin settings |
| 2026-10-14 | Docs (Claude Code, Windows) | **CR-6 recorded** (developer called it CR-5): owner can also edit slot times, about text and tagline; images/layout/design stay developer-only, image upload stays phase 2. D-09 superseded, D-23 widened, new M7.7, new C-31 (weekend days, assumed Fri+Sat). Developer decisions taken today: keep the real photos (not placeholders) in hero and gallery; weekend = Friday + Saturday; a weekday/weekend price band beats an all-days band. Plan only. | M3.1–M3.3 audit, M4.7, M7.7 |
| 2026-10-14 | Build (Claude Code, Windows) | **M3.1–M3.3 re-audit** against the restated spec. M3.1: press states for buttons, interactive cards, date chips, gallery photos; date chips 40→44px. M3.2: matches spec after CR-5 (real photos kept by decision). M3.3: no change needed. 165 passed, 15 skipped. | M4.7 slot prices |
| 2026-10-14 | Build (Claude Code, Windows) | **M4.7 slot prices** (extends M4.2). Pricing service with one resolution rule (D-47) and Fri+Sat weekend (D-46); `default_price_bdt` column + migration; API returns prices (still no customer data); price-led slot cards with non-colour states, animated selection, total in the summary; homepage price list from the same resolver. 176 passed, 15 skipped; MariaDB 11 passed. Browser-checked 360/768/1024. | M7.7 admin settings |
| 2026-10-14 | Build (Claude Code, Windows) | **M7.7 admin settings (CR-6).** Tagline, about text, booking window, confirmation note, 12 slot times (D-48, refused if upcoming bookings would be stranded), required default price, bands with add/remove/reorder and a live server-rendered price preview; dashboard price warning; `slot_times` migration. 187 passed, 15 skipped; MariaDB 11 passed + stranding query checked on MariaDB. Browser-checked 360/768/desktop with a local-only test admin. Stopping here as asked. | Deploy (pull, pip, db upgrade, restart); owner sets prices; M8.3/M8.8 |
| 2026-10-14 | Build (Claude Code, Windows) | **M5.9 admin password change.** Settings form (current/new/confirm, min 12, `Admin.set_password`), other sessions signed out through a password-hash fingerprint in the session (D-49, no migration), `reset-admin-password` CLI for recovery. Tests +7. 194 passed, 15 skipped. Added both to the §8 handover checklist and M9.3 training; recovery command in Appendix D (D14) and CLAUDE.md. | Deploy (pull, pip, db upgrade, restart); owner sets prices and changes the admin password |
| 2026-10-14 | Build (Claude Code, Windows) | **CR-7: hero uses `hero.jpg`** at the developer's request (AI-generated aerial pitch; alt text says illustration). `build_images.py` builds `static/images/hero/hero-aerial-{800,1280,1920}.webp`; `HERO` dict in `routes/public.py`; `img()` macro now takes a per-image folder, widths and size; share image and gallery unchanged. Tests: hero test added, photo test updated. 195 passed, 15 skipped. Browser: 360px loads the 800 file and fills the hero, desktop loads 1280. | Deploy with the pending pull |
| 2026-10-15 | Deploy + ops (developer + Claude Code, docs only) | **M7.7 deploy confirmed** on production: migrations to `b7e3d1f04a2c`, `db-check` OK (0.6 ms), `/`, `/book`, `/admin/login`, `/healthz` 200, API 12 slots with `price_bdt` and no customer data (prices still null: owner hasn't set them). **M8.3 done:** Force HTTPS Redirect on; external check shows 301 to https for both hosts, paths and query strings. Still to deploy: M5.9 + CR-7. Pending from ops batch 1: SECRET_KEY check (M8.1), backup script + cron swap (M8.8), host backup question (M8.4). | Ops batch 1 results, then restore test (batch 2) |
| 2026-10-15 | Ops (developer + Claude Code, docs only) | Ops batch 1 done. **M8.1:** production `SECRET_KEY` is not the leaked one. **M8.8:** nightly cron now runs `~/bin/tturf-backup.sh` (pipefail, gzip check, prune only after a good dump); test run OK. **M8.4:** host keeps JetBackup daily/weekly/monthly for about a month, self-restore from cPanel. Recorded in Appendix D; pipefail Known issue closed. | Ops batch 2: restore test |
| 2026-10-15 | Ops (developer + Claude Code, docs only) | **Restore test passed (M8.8):** newest dump restored into scratch `tturfzo1_restoretest`; counts match live and the double-booking column/index, migration id and utf8mb4 survive. Took three tries: the scratch DB was first shared with a stray new user (`tturfzo1_tturfzo1_app`), then the grant wasn't saved until **Make Changes**; `SHOW GRANTS` found it. Runbook D1 corrected (real user `tturfzo1_tturfzo1`), D15 restore test + emergency recovery added. Clean-up asked: delete the scratch DB and the stray user. M5.9 + CR-7 still not deployed (password route 404, old hero). | Batch 3: off-server copy, optional deploy key; deploy M5.9 + CR-7 |

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

## Appendix C: follow-up message to the client (2026-10-01)

> Hi! The website is built and working on my computer: the homepage, slot booking (bookings now confirm instantly, as you asked), and your admin panel where you can see bookings, cancel them, block slots, and change your phone number, WhatsApp, address, hours, rules and prices yourself.
>
> To put it online and finish it, I need these from you, most urgent first:
>
> **1. To start the next stage (payments, SMS/email alerts, customer accounts)**
> - Sign the updated project summary (version 2: Tk 30,000 total) and send the Tk 12,000 advance.
>
> **2. To put the site online**
> - The domain name you want (for example tturfzone.com), and your full name, email, phone and address to register it in your name.
> - Buy the hosting plan we choose (in your name). I'll send you the exact plan and price.
>
> **3. To take Tk 500 bKash advances (start now, approval takes 1 to 3 weeks)**
> - Trade licence, TIN, business bank account details and NID for the bKash merchant account.
>
> **4. One decision**
> - Until bKash is approved, should customers be able to book for free and pay at the ground (how it works now), or should online booking stay closed until payment works?
>
> **5. Information for the website**
> - Your price for each slot, and whether day/night or weekend prices are different.
> - Opening hours and days, and confirm the slot times (90 minutes each, 6:00 AM to 12:00 AM).
> - How many days ahead customers can book (now 14).
> - Exact address and your Google Maps location link.
> - Phone number for calls and WhatsApp number for bookings.
> - Your booking, cancellation and refund rules.
> - Your email for the admin login, and anyone else who will manage bookings.
> - Phone number and email where you want new-booking alerts.
>
> **6. Photos and text**
> - Your logo (best quality you have).
> - 10 to 15 original photos straight from your phone: day, night under lights, the full field, facilities. Please don't download them from Facebook, it lowers the quality.
> - A short video if you have one.
> - ~~The facilities you actually have (parking, changing room, water, etc.).~~ (CR-5: no longer needed)
> - A short description of the turf (2 to 4 sentences) and a one-line tagline.
> - Any real customer reviews you're happy to show, with their permission.
> - Confirm your Facebook page link and any other social links, and the sports you offer.
>
> **7. Customer accounts (quick yes/no)**
> - Customers will never be forced to make an account to book. OK?
> - Logged-in customers stay logged in for 60 days. OK?

Developer notes (not for the client): items map to C-01, C-02, C-04…C-08, C-10, C-12…C-21, C-23…C-30. C-03, C-09, C-11 and C-22 are obsolete or answered (CR-2, D-40). C-26 (SMS provider) is left to the developer unless the client has a preference.


## Appendix D: production deploy runbook (cPanel Terminal, no SSH; CR-4)

**As deployed (2026-10-13).** The first install cloned the repo with `git clone` in cPanel Terminal using the token, then removed the token from the remote (`git remote set-url origin https://github.com/TanjimEram/WEB_TTurfZone.git`). cPanel's Git Version Control screen was not usable because it rejects tokens in the clone URL. D3 below does the same job without the token ever touching the remote, and it is the one to use for updates.

**Updating production** (after a push to `main`): run D5 (helper), then D3 (pull), then:
```bash
tz pip install -q -r requirements.txt && tz flask --app app db upgrade && tz flask --app app db-check && touch /home/tturfzo1/tturfzone/tmp/restart.txt && echo UPDATED
```
Then repeat D12 and D13. Before any update that changes models or migrations, run `pytest -q -m mariadb` locally first.

**Cron jobs (cPanel → Cron Jobs), added 2026-10-13:**
- **Nightly backup**, schedule `0 3 * * *` (since 2026-10-15):
  ```
  /bin/bash /home/tturfzo1/bin/tturf-backup.sh > /dev/null
  ```
  The script (`~/bin/tturf-backup.sh`, chmod 700, created with one `printf` line in Terminal) dumps `tturfzo1_tturfzone` with `--single-transaction --default-character-set=utf8mb4` through gzip into a `.tmp` file, stops on any error (`set -euo pipefail`), checks the file with `gzip -t`, renames it to `tturfzone-YYYY-MM-DD.sql.gz` and only then deletes `tturfzone-*.sql.gz` older than 14 days. Credentials come from `~/.my.cnf` (chmod 600, built from `~/.tturfzone_db`); no password in the cron line, and no `%` left to escape. Success prints nothing (`> /dev/null`); errors go to the cron email. Before 2026-10-15 the job was one inline `mysqldump | gzip && find` line, which hid a failed dump.
- **Host backups:** cPanel → JetBackup (daily / weekly / monthly, about one month, self-restore). Separate from ours.
- **Keep-alive**, schedule `*/5 * * * *` (keeps Passenger from putting the idle app to sleep; no database involved, D-12):
  ```
  curl -s https://tturfzone.com/healthz > /dev/null 2>&1
  ```
- Not yet: the CR-1 jobs (M8.5), which need M11.

The plan has no SSH, so every command is pasted into cPanel → Terminal. That terminal mangles multi-line pastes, so each step is **one line**. Run them one at a time and read the output before the next. No secret is ever typed on a command line: passwords and tokens are read at hidden prompts.

**D1 (cPanel UI, once).** MySQL Databases: create database `tturfzone` (cPanel names it `tturfzo1_tturfzone`) and a user with the password generator, then add the user to the database with ALL PRIVILEGES (**Add**, then tick ALL PRIVILEGES, then **Make Changes**: nothing is saved until that last click). cPanel prefixes the name you type with `tturfzo1_`: **the production user is `tturfzo1_tturfzo1`** (it is also the user in `~/.my.cnf`). Keep the password in a password manager.

**D2 Store the connection string** (`~/.tturfzone_db`, chmod 600, outside the repo; the password is URL-encoded):
```bash
read -rp 'DB name (e.g. tturfzo1_tturfzone): ' N; read -rp 'DB user (e.g. tturfzo1_app): ' U; read -rsp 'DB password: ' P; echo; E=$(printf %s "$P" | /home/tturfzo1/virtualenv/tturfzone/3.11/bin/python -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read(),safe=""),end="")'); printf 'mysql+pymysql://%s:%s@localhost/%s?charset=utf8mb4' "$U" "$E" "$N" > ~/.tturfzone_db && chmod 600 ~/.tturfzone_db && unset P E && echo "SAVED, mode $(stat -c %a ~/.tturfzone_db)"
```
Then in cPanel → Setup Python App → the app → Environment variables, set `DATABASE_URL` to the same value (`cat ~/.tturfzone_db; echo` shows it; `clear` afterwards).

**D3 Get the code** (clones on first run, fast-forward pulls after). Use a fine-grained GitHub token: this repo only, Contents read-only, short expiry. It is sent as a one-off request header, so it never lands in the remote URL or `.git/config`:
```bash
cd /home/tturfzo1/tturfzone && read -rsp 'GitHub token: ' T; echo; H="Authorization: Basic $(printf 'x:%s' "$T" | base64 -w0)"; if [ -d .git ]; then git -c http.extraHeader="$H" pull --ff-only origin main; else git init -q && git remote add origin https://github.com/TanjimEram/WEB_TTurfZone.git && git -c http.extraHeader="$H" fetch -q origin main && git checkout -q -f -B main origin/main && git branch -q -u origin/main; fi; unset T H; git log --oneline -1; git remote get-url origin; grep -qiE 'ghp_|github_pat_|authorization' .git/config && echo 'TOKEN FOUND IN CONFIG - STOP' || echo 'NO TOKEN IN CONFIG'
```
`checkout -f` replaces the cPanel-generated `passenger_wsgi.py` with ours; `tmp/` is left alone.

**D4 Install dependencies:**
```bash
source /home/tturfzo1/virtualenv/tturfzone/3.11/bin/activate && cd /home/tturfzo1/tturfzone && pip install -q -r requirements.txt && python --version && python -c "import pymysql, flask, sqlalchemy; print('DEPS OK')"
```

**D5 Define a helper for this terminal session** (production config, URL from `~/.tturfzone_db`; the throwaway `SECRET_KEY` is fine because CLI commands sign nothing). Run it again whenever the terminal is reopened:
```bash
tz() { source /home/tturfzo1/virtualenv/tturfzone/3.11/bin/activate && cd /home/tturfzo1/tturfzone && APP_ENV=production SECRET_KEY=terminal-cli-only DATABASE_URL="$(cat ~/.tturfzone_db)" "$@"; }; echo HELPER READY
```

**D6** `tz flask --app app db-check` (expect "tables are missing" plus the round trip) → **D7** `tz flask --app app db upgrade && tz flask --app app db-check` (expect "Database OK") → **D8** `tz flask --app app seed-settings` → **D9** `tz flask --app app create-admin --username <name>` (save the printed password immediately; it is shown once).

**D10 Check the schema and the server:**
```bash
tz python -c "from app import create_app; from extensions import db; from sqlalchemy import text; app = create_app(); app.app_context().push(); print(db.session.execute(text('SHOW CREATE TABLE bookings')).one()[1]); print(db.session.execute(text('SELECT VERSION(), @@wait_timeout, @@character_set_server, @@lower_case_table_names')).one())"
```
Expect `active_slot_key ... GENERATED ALWAYS AS (case when status in ('PENDING','CONFIRMED','BLOCKED') ...) STORED`, `UNIQUE KEY uq_active_slot_key`, and `CHARSET=utf8mb4`.

**D11 Restart:** `mkdir -p /home/tturfzo1/tturfzone/tmp && touch /home/tturfzo1/tturfzone/tmp/restart.txt && echo RESTARTED`

**D12 Verify over HTTPS** (status + certificate check per URL, http→https redirects, security headers):
```bash
D=$(TZ=Asia/Dhaka date -d tomorrow +%F); for u in https://tturfzone.com/healthz https://www.tturfzone.com/healthz https://tturfzone.com/ "https://tturfzone.com/api/availability?date=$D" https://tturfzone.com/dev/wiring https://tturfzone.com/admin/login; do echo "$(curl -s -o /dev/null -w '%{http_code} ssl_verify=%{ssl_verify_result}' "$u")  $u"; done; echo "healthz body: $(curl -s https://tturfzone.com/healthz)"; curl -sI http://tturfzone.com/ | grep -iE '^(HTTP|location)'; curl -sI http://www.tturfzone.com/ | grep -iE '^(HTTP|location)'; curl -sI https://tturfzone.com/ | grep -iE '^(x-content-type-options|x-frame-options|referrer-policy)'
```
Expect 200 everywhere except `/dev/wiring` (404), `ssl_verify=0` (certificate valid), a 301 to `https://` from both http URLs, and all three headers.

**D13 Availability API holds 12 slots and no customer data:**
```bash
curl -s "https://tturfzone.com/api/availability?date=$(TZ=Asia/Dhaka date -d tomorrow +%F)" | /home/tturfzo1/virtualenv/tturfzone/3.11/bin/python -c "import sys,json; s=json.load(sys.stdin)['slots']; k=sorted({x for row in s for x in row}); print(len(s), 'slots, keys', k); print('NO CUSTOMER DATA' if k == ['label','price_bdt','state','time'] else 'UNEXPECTED KEYS - STOP')"
```

**D14 Recover a lost admin password** (run D5 first). Prints a new 20-character password once and signs out every session:
```bash
tz flask --app app reset-admin-password --username <name>
```
Give it to the owner privately and ask them to change it from Settings → "Change your password".

**D15 Restore test (do it after any change to the backup job, and before handover).** Proves a backup actually restores, without touching the live database:
1. cPanel → MySQL Databases: create database `restoretest` (→ `tturfzo1_restoretest`); Add User To Database: user `tturfzo1_tturfzo1`, database `tturfzo1_restoretest` → **Add** → tick ALL PRIVILEGES → **Make Changes**. Check: `mariadb --defaults-file=$HOME/.my.cnf -N -e "SHOW GRANTS" | grep restoretest` prints one GRANT line.
2. Restore the newest dump and compare (expect equal counts, then `STORED`, `UNIQUE KEY` `uq_active_slot_key`, the current migration id and `utf8mb4_unicode_ci`):
```bash
F=$(ls -t ~/backups/tturfzone-*.sql.gz | head -1); echo "restoring $F into tturfzo1_restoretest"; gunzip -c "$F" | mariadb --defaults-file=$HOME/.my.cnf tturfzo1_restoretest && for t in admins bookings turf_settings alembic_version; do echo "$t: live=$(mariadb --defaults-file=$HOME/.my.cnf -N -e "SELECT COUNT(*) FROM tturfzo1_tturfzone.$t") restored=$(mariadb --defaults-file=$HOME/.my.cnf -N -e "SELECT COUNT(*) FROM tturfzo1_restoretest.$t")"; done; mariadb --defaults-file=$HOME/.my.cnf -N -e "SELECT version_num FROM tturfzo1_restoretest.alembic_version; SHOW CREATE TABLE tturfzo1_restoretest.bookings" | grep -oE "b7e3d1f04a2c|UNIQUE KEY .uq_active_slot_key.|STORED|utf8mb4_unicode_ci" | sort -u
```
3. Delete `tturfzo1_restoretest` in cPanel.

**Real recovery (emergency only).** Prefer cPanel → JetBackup → Database Backups → restore `tturfzo1_tturfzone` from a date. From our own dump instead: take a fresh dump first (`bash ~/bin/tturf-backup.sh`, which keeps today's file name, so copy the file you want to restore elsewhere before running it), then `gunzip -c <file> | mariadb --defaults-file=$HOME/.my.cnf tturfzo1_tturfzone`. The dump drops and recreates each table, so anything written after it was taken is lost. Restart the app afterwards.

Never run `fake-*` commands on production. They are not even registered there (`ENABLE_DEV_TOOLS` is off).
