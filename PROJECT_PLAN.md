# TTURFZONE project plan (living document)

> For Claude: this file is the project's memory across sessions and accounts. Read "Resume here" first. Update it in the same commit as the work (rules in CLAUDE.md). Never write passwords, API keys or connection strings in this file.

## Resume here

| Field | Value |
|---|---|
| Phase | M0 pre-build (no code yet) |
| Last completed | Planning session: brief reviewed, hosting options researched, CLAUDE.md and this plan written (2026-09-10) |
| Next task | M0.1 Send the client message (Appendix A) and collect decisions C-01 to C-11 |
| Blocked by | Client decisions; hosting choice (M0.3) |
| Live URL | not deployed |
| Repo | not created |

Status keys: `[ ]` to do, `[x]` done, `~~struck through~~ (CR-n)` dropped by a change request.

---

## 1. Snapshot

- Client: TTURFZONE turf ground owner. Facebook: https://www.facebook.com/TTURFZONE
- Found online (confirm with owner): listed on Book My Turf BD as "T Turf Zone", 6-a-side futsal, Notin Rani ghat, New Jailkhana, inside Tripti Sporting Club.
- Reference site, inspiration only, do not copy: https://turfxsonagazi.com
- Brief: `docs/brief/TTURFZONE_Claude_Code_Project_Brief.pdf`
- Budget: ৳10,000. Delivery: 2 days. Built with Claude Code.
- Definition of done (brief §19): on a phone, a customer selects a date, selects an available 90-minute slot, submits name and phone, and sees a booking ID with PENDING status. The owner logs in securely, sees the request, confirms or rejects it, and blocks slots. Production runs on HTTPS with the production database connected, and duplicate-booking conflicts have been tested.

## 2. Global constraints (from the brief; change only through a CR)

- No online payment in the MVP. A booking is a request; the owner confirms or rejects it.
- Statuses: PENDING (awaiting owner), CONFIRMED (accepted, unavailable to others), REJECTED (declined, slot free again), BLOCKED (owner prevents booking).
- Fixed 90-minute slots: 06:00, 07:30, 09:00, 10:30, 12:00, 13:30, 15:00, 16:30, 18:00, 19:30, 21:00, 22:30.
- Duplicate bookings are prevented on the server/database side. Client-side availability is never trusted.
- Mobile-first. Persistent mobile actions: WHATSAPP and BOOK NOW.
- Never invent business information. Use `TODO(owner):` placeholders for missing data.
- Reviews: only genuine, owner-approved. Facebook: link only, no Facebook API.
- WhatsApp: deep link only, no paid messaging API.
- Secrets only in environment variables. Passwords hashed. Admin routes protected. HTTPS in production. Customer booking data never public.
- Readable, beginner-friendly code. Separate config, models, routes, services and templates. No unnecessary dependencies.
- Excluded from MVP: online payments/bKash, customer accounts, SMS gateway, automated WhatsApp API, multiple branches, tournaments, coupons/loyalty, complex analytics, native app, AI chatbot, large CMS.
- Visual direction (unless the owner's brand says otherwise): dark base, energetic green accent, white typography, high-contrast CTAs, large real photos, clean cards, restrained motion.

## 3. Decisions

| ID | Decision | Why | Status |
|---|---|---|---|
| D-01 | Flask + Jinja + vanilla JS + PostgreSQL | Brief §8 | Final |
| D-02 | Database: use the hosting plan's own PostgreSQL if it has one with backups; otherwise Neon Free (region nearest the app server). Not Supabase Free. | Supabase Free pauses a project after 7 days without activity and has no downloadable backups. Neon Free scales to zero after 5 idle minutes and wakes automatically in milliseconds. | Proposed, finalize in M0.3 |
| D-03 | App hosting: Bangladeshi cPanel hosting with Python app support (Passenger), paid in BDT, account in the owner's name. Fallback: Render Starter (about $7/month, needs an international card) + Neon. | No cold starts, bKash payment, local support, low yearly cost. Free Render/Koyeb tiers sleep, which is bad for a booking site opened from Facebook. | Proposed, finalize in M0.3 |
| D-04 | Blocks are rows in `bookings` with status BLOCKED (reason in `admin_note`). No separate BlockedSlot table. | One partial unique index then prevents every conflict (booking vs booking, booking vs block). Brief §2 already treats BLOCKED as a booking status; brief §10 allows schema refinement. | Final unless developer objects |
| D-05 | A PENDING request holds its slot until the owner confirms or rejects. Max 2 future PENDING requests per phone number. | Matches brief §2 (REJECTED frees the slot). The cap limits spam. | Confirm with owner (C-03) |
| D-06 | Owner can reject a CONFIRMED booking too (shown as "Cancel") | Real customers cancel; the owner must be able to free the slot | Final |
| D-07 | Plain CSS with custom properties, no Tailwind build step | Nothing to compile on cPanel; fewer moving parts | Final |
| D-08 | Dependencies: Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF, psycopg[binary], python-dotenv, tzdata; dev: pytest. Add gunicorn only if deploying to Render. | Flask-Migrate: future schema changes on live data. Flask-WTF: CSRF protection. tzdata: zoneinfo on Windows has no timezone database. | Final |
| D-09 | Slot times are a constant in `services/slots.py` for the MVP | Settings-driven slot config is future work (Backlog) | Final |
| D-10 | Business logic uses Asia/Dhaka time (`zoneinfo`). Slots stored as local `date` + `time`; audit fields as `timestamptz`. | Server may run in UTC | Final |
| D-11 | Success page reads the booking from the session (one-time), no public `/booking/<code>` URL | Brief §13: do not expose customer data publicly | Final |
| D-12 | `/healthz` does not touch the database | Uptime pings must not keep Neon awake and burn free compute hours | Final |
| D-13 | Owner content (about, facilities, reviews, pricing, gallery list, contact, hours) lives in one `turf_settings` row, seeded from `database/seed_data.py` | One place to edit; admin settings page (M7.4) can edit it later | Final |
| D-14 | Admin password generated by `create-admin` (20 random chars, shown once). Login rate limiting moved to Backlog. | Fits the 2-day window; strong generated password lowers brute-force risk | Final |
| D-15 | ৳10,000 is the development fee. Domain and hosting are billed to the owner separately and registered in the owner's name. | Recurring costs belong to the owner; clean handover | Confirm with owner (C-09) |

## 4. Infrastructure and accounts (no secrets here)

| Service | Purpose | Account owner | Status | Notes |
|---|---|---|---|---|
| Domain (.com preferred) | Website address | Owner is registrant; developer has access | Not bought | Buy from the chosen host. Record renewal date and renewal price. |
| Hosting (BD cPanel, Python) | Runs Flask app | Owner's email; login shared privately | Not chosen | Must pass Appendix B checks before paying |
| PostgreSQL | Production DB | Owner's email | Not created | Host PostgreSQL or Neon (D-02). Neon: create `production` and `dev` branches. |
| GitHub (private repo) | Code | Developer; add owner or transfer at handover if agreed | Not created | |
| Google Maps | Map embed + directions link | None | n/a | Embed iframe and share link, no API key |

Credentials are handed to the owner privately (in person or a password manager share), never through this repo.

## 5. Architecture and contracts

### 5.1 File map

```
tturfzone/
├── CLAUDE.md
├── app.py                    # create_app(), registers blueprints, CLI commands, security headers
├── config.py                 # DevConfig, TestConfig, ProdConfig (read from env)
├── extensions.py             # db = SQLAlchemy(), migrate = Migrate(), csrf = CSRFProtect()
├── cli.py                    # create-admin, seed-settings, db-check
├── passenger_wsgi.py         # cPanel entry: from app import create_app; application = create_app()
├── requirements.txt
├── .env.example
├── .gitignore                # .env, .venv, __pycache__, instance/, *.sqlite
├── docs/
│   ├── PROJECT_PLAN.md
│   └── brief/TTURFZONE_Claude_Code_Project_Brief.pdf
├── models/
│   ├── __init__.py           # exports Admin, Booking, TurfSettings
│   ├── admin.py
│   ├── booking.py
│   └── turf_settings.py
├── routes/
│   ├── __init__.py
│   ├── public.py             # blueprint "public": /, /book, /book/success, /healthz
│   ├── api.py                # blueprint "api": /api/availability
│   └── admin.py              # blueprint "admin": /admin/...
├── services/
│   ├── __init__.py
│   ├── slots.py              # slot constants, Dhaka time, bookability, day availability
│   ├── bookings.py           # create/confirm/reject/block/unblock, validation, codes
│   └── auth.py               # login_required, verify_admin
├── templates/
│   ├── base.html
│   ├── partials/             # nav, footer, sticky_actions, slot_grid, flash
│   ├── index.html
│   ├── booking.html
│   ├── booking_success.html
│   ├── errors/404.html, errors/500.html
│   └── admin/ base_admin.html, login.html, dashboard.html, bookings.html, calendar.html, settings.html
├── static/
│   ├── css/ main.css, admin.css
│   ├── js/ booking.js, gallery.js, reveal.js, admin.js
│   ├── images/ hero/, gallery/, og-image.jpg, logo.*
│   └── icons/
├── database/
│   ├── migrations/           # Flask-Migrate (Migrate(app, db, directory="database/migrations"))
│   └── seed_data.py          # TurfSettings defaults with TODO(owner) placeholders
└── tests/
    ├── conftest.py
    ├── test_slots.py
    ├── test_bookings.py
    ├── test_bookings_concurrency.py   # @pytest.mark.postgres
    ├── test_public_routes.py
    └── test_admin_routes.py
```

### 5.2 Data model

**admins**: id (PK), username (unique, not null), password_hash (not null, werkzeug `generate_password_hash`), created_at (timestamptz).

**bookings**: id (PK), booking_code (unique, e.g. `TZ-7K3M9Q`), customer_name (nullable for BLOCKED), phone (nullable for BLOCKED, normalized `01XXXXXXXXX`), booking_date (date), slot_time (time), status (`PENDING|CONFIRMED|REJECTED|BLOCKED`), admin_note (text, nullable; block reason or rejection note), created_at, updated_at (timestamptz).

Conflict rule, enforced by the database:

```python
__table_args__ = (
    db.Index(
        "uq_active_slot", "booking_date", "slot_time", unique=True,
        postgresql_where=db.text("status IN ('PENDING','CONFIRMED','BLOCKED')"),
        sqlite_where=db.text("status IN ('PENDING','CONFIRMED','BLOCKED')"),
    ),
    db.Index("ix_bookings_status_date", "status", "booking_date"),
    db.CheckConstraint("status IN ('PENDING','CONFIRMED','REJECTED','BLOCKED')", name="ck_booking_status"),
)
```

Alembic autogenerate can miss the WHERE clause. Always open the generated migration and check it.

**turf_settings** (single row, id = 1): turf_name, tagline, about_text, phone, whatsapp (digits with country code, e.g. `8801XXXXXXXXX`), address, map_embed_url, map_link, facebook_url, opening_hours_text, booking_rules_text, confirm_time_text, booking_window_days (int, default 14), max_pending_per_phone (int, default 2), pricing (JSON), facilities (JSON), reviews (JSON), gallery (JSON), updated_at.

Pricing JSON shape (final values from C-02):

```json
[{"label": "Morning", "slots": ["06:00", "07:30", "09:00"], "days": "all", "price_bdt": 0}]
```

`days` is `all`, `weekday` or `weekend`. If the owner has one flat price, use a single band with all 12 slots.

### 5.3 Service contracts

`services/slots.py`
- `SLOT_TIMES: list[datetime.time]` (the 12 slots), `SLOT_MINUTES = 90`, `TZ = ZoneInfo("Asia/Dhaka")`
- `now_dhaka() -> datetime`
- `slot_label(t: time) -> str` returns `"06:00 AM"` style
- `is_valid_slot(t: time) -> bool`
- `booking_window(today: date, days: int) -> list[date]` (today plus the next `days - 1` days)
- `is_bookable(d: date, t: time, now: datetime | None = None) -> bool` (valid slot, slot start in the future, date inside window)
- `get_day_availability(d: date) -> list[dict]` returns `{"time": "06:00", "label": "06:00 AM", "state": "available|pending|booked|blocked|past", "price_bdt": int | None}`. No customer data.

`services/bookings.py`
- `class BookingValidationError(Exception)` with `.errors: dict[str, str]`
- `class SlotUnavailableError(Exception)`
- `class InvalidTransitionError(Exception)`
- `normalize_phone(raw: str) -> str` accepts `01XXXXXXXXX`, `+8801...`, `8801...`; regex `^01[3-9]\d{8}$` after normalizing; raises `BookingValidationError`
- `generate_booking_code() -> str` (`TZ-` + 6 chars from `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`, `secrets`)
- `create_booking_request(name: str, phone: str, booking_date: date, slot_time: time) -> Booking` validates, checks pending cap, inserts, catches `IntegrityError` and raises `SlotUnavailableError`
- `confirm_booking(booking_id: int) -> Booking` (PENDING only)
- `reject_booking(booking_id: int, note: str | None = None) -> Booking` (PENDING or CONFIRMED)
- `block_slot(booking_date: date, slot_time: time, reason: str) -> Booking` raises `SlotUnavailableError` if taken
- `unblock_slot(booking_id: int) -> None` deletes the BLOCKED row
- `dashboard_summary(today: date) -> dict` with keys `today`, `pending_count`, `upcoming`

`services/auth.py`
- `verify_admin(username: str, password: str) -> Admin | None`
- `login_required` decorator; session key `admin_id`; `session.clear()` on login and logout

### 5.4 Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Homepage with all sections and quick booking grid |
| GET | `/book?date=&slot=` | Booking page, preselects date/slot |
| POST | `/book` | Create request (CSRF), redirect to success or re-render with errors |
| GET | `/book/success` | One-time confirmation from session |
| GET | `/api/availability?date=YYYY-MM-DD` | Public slot states (JSON) |
| GET | `/healthz` | Returns `ok`, no DB |
| GET, POST | `/admin/login` | Owner login |
| POST | `/admin/logout` | Logout |
| GET | `/admin/` | Dashboard |
| GET | `/admin/bookings?date=&status=` | Filterable list |
| POST | `/admin/bookings/<id>/confirm` | Confirm |
| POST | `/admin/bookings/<id>/reject` | Reject or cancel |
| GET | `/admin/calendar?date=` | 12-slot day view with actions |
| POST | `/admin/slots/block` | Block (date, slot_time, reason) |
| POST | `/admin/slots/<id>/unblock` | Unblock |
| GET, POST | `/admin/settings` | Basic settings (M7.4) |

WhatsApp link after booking: `https://wa.me/<whatsapp>?text=` + URL-encoded `"Hi, I requested a booking at TTURFZONE. Booking ID: TZ-XXXXXX, Date: ..., Time: ..."`.

### 5.5 Environment variables (`.env.example` lists names only)

`APP_ENV` (development|testing|production), `SECRET_KEY`, `DATABASE_URL` (`postgresql+psycopg://...`, add `?sslmode=require` for Neon), `TEST_DATABASE_URL` (optional, for the postgres test).

Engine options: `pool_pre_ping=True`, `pool_recycle=280` (Neon closes idle connections when it scales to zero).

Production config: `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"`, `PERMANENT_SESSION_LIFETIME=12h`. Response headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.

---

## 6. Milestones and tasks

Times are targets. If a milestone runs over by more than an hour, tell the developer and propose what to cut (log it as a CR).

### M0 Pre-build (Day 0)

- [ ] M0.1 Send client message (Appendix A). Collect C-01 to C-11 answers.
- [ ] M0.2 Agree budget split with client (C-09, D-15).
- [ ] M0.3 Shortlist 2 Bangladeshi Python hosting plans. Ask Appendix B questions through their live chat. Pick one; finalize D-02 and D-03.
- [ ] M0.4 Buy hosting + domain in the owner's name (owner pays). Enable AutoSSL. Do this before Day 1 starts: DNS and SSL can take hours.
- [ ] M0.5 If Neon: create project (region nearest the host server) with `production` and `dev` branches.
- [ ] M0.6 Create private GitHub repo. Commit CLAUDE.md, docs/PROJECT_PLAN.md, brief PDF.
- [ ] M0.7 Local setup: Python version matching the host (3.10+), Git, editor, Claude Code.

Done when: repo exists with docs, hosting and DB are accessible, C-01 to C-07 answered.

### M1 Scaffold and walking-skeleton deploy (Day 1, 09:00 to 10:30)

- [ ] M1.1 `requirements.txt`, `.gitignore`, `.env.example`, `config.py`, `extensions.py`, `app.py` (factory, blueprints, headers), `cli.py` with `db-check`, `templates/base.html`, `/healthz`.
- [ ] M1.2 `tests/conftest.py` (app with TestConfig, SQLite in-memory, CSRF off in tests), one test for `/healthz`.
- [ ] M1.3 Deploy skeleton to the host: `passenger_wsgi.py`, Setup Python App, env vars, `pip install`, `flask db-check` from the host terminal.

Done when: `pytest -q` passes; host URL (temporary URL is fine) returns `ok` at `/healthz`; `db-check` succeeds on the host. This proves the risky parts early.

### M2 Data model and booking rules (Day 1, 10:30 to 12:30)

- [ ] M2.1 Models (5.2), Flask-Migrate at `database/migrations`, first migration, verify partial index WHERE clause.
- [ ] M2.2 `services/slots.py` + `tests/test_slots.py`: 12 valid slots, past slot today not bookable, outside window not bookable, Dhaka time used (freeze `now`).
- [ ] M2.3 `services/bookings.py` + `tests/test_bookings.py`: valid create, name/phone validation, phone normalization, same slot twice raises `SlotUnavailableError`, reject frees slot, block prevents booking, pending cap per phone, confirm only from PENDING.
- [ ] M2.4 `tests/test_bookings_concurrency.py` (`@pytest.mark.postgres`): 10 threads book the same slot; exactly 1 succeeds. Run against Neon `dev` branch or local Postgres.
- [ ] M2.5 `cli.py`: `create-admin`, `seed-settings` using `database/seed_data.py` (placeholders only).

Done when: all tests pass, including the postgres marker.

### M3 Homepage (Day 1, 12:30 to 14:30)

- [ ] M3.1 `static/css/main.css`: design tokens, type scale, buttons and cards with hover/press states, mobile-first grid, focus states.
- [ ] M3.2 `index.html` sections: hero, quick booking placeholder, about, facilities, pricing, gallery grid, location (map embed + GET DIRECTIONS), reviews, Facebook, footer (address, phone, WhatsApp, Facebook, hours, quick links, copyright, booking disclaimer). All content from `turf_settings`.
- [ ] M3.3 Nav with smooth scroll; sticky mobile bar (WHATSAPP + BOOK NOW); floating WhatsApp button on desktop.

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

Done when: `https://<domain>` loads, http redirects to https, admin login works on production.

### M9 QA and handover (Day 2, 17:00 to 21:00)

- [ ] M9.1 Full QA checklist on a real Android phone, an iPhone if available, and desktop.
- [ ] M9.2 Production duplicate-booking test: two phones submit the same slot at the same moment; one succeeds. Delete test rows.
- [ ] M9.3 Owner training: 10-minute screen recording in Bangla (log in, confirm, reject, cancel, block, settings).
- [ ] M9.4 Handover pack delivered privately: accounts list, credentials, renewal dates and prices, how to request changes, support terms.
- [ ] M9.5 Set the Facebook page action button to the website booking page; add the site to Google Business Profile if one exists.
- [ ] M9.6 Tag `v1.0.0`; final plan update.

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

**D. Security**
- [ ] No secrets in the repo (`git grep -i "password\|secret\|postgres://"` shows only names/placeholders)
- [ ] CSRF token required on all POST forms in production config
- [ ] `/api/availability` contains no customer data
- [ ] Session cookie has Secure, HttpOnly, SameSite in production

**E. Production**
- [ ] HTTPS on root and www; http redirects
- [ ] Production DB connected; migrations applied
- [ ] Duplicate-booking test done on production (M9.2)
- [ ] 404 page shows for unknown URLs; no debug tracebacks

## 8. Handover checklist

- [ ] Owner can log in to the admin on their own phone
- [ ] Owner has domain and hosting logins (in owner's name) and knows renewal dates
- [ ] Training video delivered
- [ ] Owner knows what the site does not do yet (no online payment, no auto SMS)
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

## 10. Change requests

| ID | Date | Request | Type (add/remove/modify) | Impact (time, scope, price) | Affected tasks | Status |
|---|---|---|---|---|---|---|

No change requests yet.

## 11. Backlog (after MVP)

- Online payment (bKash/Nagad/SSLCommerz) with advance deposit
- Automatic confirmations (SMS or WhatsApp Business API)
- Auto-expire PENDING requests after X hours
- Customer self-cancel with a code
- Login rate limiting and lockout
- Admin editing for about, facilities, gallery and reviews
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

## 13. Known issues

None yet.

## 14. Session log

| Date | Session | What was done | Next |
|---|---|---|---|
| 2026-09-10 | Planning (claude.ai) | Reviewed brief; researched hosting/DB options; wrote CLAUDE.md and this plan | M0.1 |

---

## Appendix A: message to send the client

> Hi! To start building the TTURFZONE website, I need a few things from you.
>
> By tonight:
> 1. The domain name you want (for example tturfzone.com) and your full name, email, phone and address for registering it in your name.
> 2. Confirm that the domain and hosting (roughly ৳4,000 to ৳5,000 per year) are paid separately from the ৳10,000 website fee.
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
