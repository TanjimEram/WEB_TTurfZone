# TTURFZONE: instructions for Claude

@docs/PROJECT_PLAN.md

## What this project is

Website and self-sufficient slot-booking system for TTURFZONE, a single turf ground in Bangladesh.
Flask + Jinja templates + vanilla JS. Production database: MariaDB 11.4 on the cPanel host (CR-4); PostgreSQL stays supported; SQLite for the fast local tests. Built by one developer with Claude Code, then handed to the owner.

**How booking works now (CR-9, built; sign-in optional since CR-13):** the customer signs in with Google (optional), pays a ৳500 advance by bKash
*Payment* to the owner's merchant number, and submits the TrxID and the number paid from. The booking is
`PENDING` ("payment being checked") and holds its slot until the owner confirms or rejects it in the admin;
a signed-in customer is then emailed from tturfzone@gmail.com through the Gmail API; a guest gets no email and the owner calls or WhatsApps them. `PAYMENTS_ENABLED=false` means
this flow.

**Later, if the owner gets bKash Payment Gateway keys (CR-1, not built):** online payment verified
server-to-server and automatic confirmation (`PAYMENTS_ENABLED=true`, `PENDING_PAYMENT` holds that expire after
`HOLD_MINUTES`), SMS notifications and scheduled jobs. See CR-1 in the plan.

- Original MVP scope: `docs/brief/TTURFZONE_Claude_Code_Project_Brief.pdf`
- CR-1 (self-sufficient architecture) overrides the brief where the plan's Change requests / Decisions say so.
- Living plan, decisions and progress: `docs/PROJECT_PLAN.md` (imported above)

If the brief and the plan disagree, the plan wins only where a Decision (D-n) or Change Request (CR-n) says so. Otherwise the brief wins.

## Start of every session

1. Read "Resume here" at the top of PROJECT_PLAN.md.
2. Run `git status` and `git log --oneline -10`. If the code and the plan disagree, trust the code, correct the plan, and note it in the session log.
3. Tell the developer in 3 to 5 lines: last completed task, next task, blockers. Wait for a go-ahead before starting a new milestone.

## While working

- One task at a time, in plan order, unless the developer says otherwise.
- Before a major architectural choice, explain it in a few sentences and get agreement. Record it in the Decisions table.
- Write or update tests together with the code. Run `pytest -q` before marking a task done.
- Commit after each task: `git commit -m "<type>(<task id>): <summary>"`. Types: feat, fix, test, docs, chore, style.
- After each completed milestone: run `pytest -q`, then `git push` to `origin`.
- Never invent business information (prices, facilities, reviews, hours, address). Use `TODO(owner): ...` placeholders and make sure each one appears in the Client inputs table. The notes show in development only; production hides them and the empty sections (`SHOW_TODO_NOTES`, D-50), and the admin dashboard lists what is missing.
- Photos: only real photos of the ground (the CR-7 illustration hero was removed by CR-12). Background textures and the turf glow are drawn in CSS or cut from the owner's own photos, never stock. Originals go in `assets_raw/` (gitignored); run `python scripts/build_images.py` and commit the output (D-45).
- Prefer the simplest implementation that meets the brief. Note assumptions in the Decisions table.

## End of every task (mandatory)

In the same commit as the code, update PROJECT_PLAN.md:

- tick the task checkbox and update "Resume here"
- add one line to the Session log (date, task, result, next step)
- record anything new in Decisions, Risks or Known issues

## When the developer adds, removes or changes a feature

1. Add a row to Change requests (CR-n) with the impact on time, scope and price.
2. New work gets new task ids (for example `M4.7`). Never delete old tasks; strike them through and reference the CR: `~~M7.4 Admin settings page~~ (CR-2)`.
3. Anything outside the MVP goes to the Backlog unless the developer says to build it now.
4. Only change Global constraints when the developer explicitly overrides the brief, and cite the CR.

## Hard rules

- No secrets in git or in any .md file. Secrets live in `.env` locally and in the host's environment settings. `.env.example` lists variable names only.
- Double booking is prevented by the database: partial unique index `uq_active_slot` on PostgreSQL/SQLite, generated column `active_slot_key` + unique index `uq_active_slot_key` on MariaDB (D-42, plan §5.2). Frontend checks are only for UX.
- Customer names and phone numbers appear only on admin pages behind login. The availability API never returns them.
- All "today", "past slot" and booking-window logic uses Asia/Dhaka time via `services/slots.now_dhaka()`, never server time.
- `/healthz` must not query the database.
- No new dependency without a one-line justification in the Decisions table.
- Beginner-readable code: small functions, docstrings on service functions, no clever tricks, no giant app.py.

Payments and notifications (CR-1):

- Never mark a booking paid from a redirect or query parameter. Verify every payment server-to-server with the gateway and check the amount and `merchant_invoice` before confirming.
- Payment callbacks must be idempotent: the same callback delivered twice must not double-confirm or double-notify.
- Booking creation must expire stale holds for that slot (in the same transaction) before inserting the new row.
- Notification sending must never block, fail or roll back a booking. A failed SMS or email is retried by the outbox job, never surfaced as a booking error.
- Gateway, SMS and SMTP credentials live only in environment variables. Never log credentials, tokens, or full raw requests/responses that contain them.
- Unit tests never call real gateways or SMS/email providers; use fakes. Real sandbox calls go only in tests marked `@pytest.mark.sandbox`, which skip without credentials.

Customer accounts (CR-3):

- Never store or log a plain OTP code. Only `code_hash` is stored; never write the code itself to logs, flash messages, or error text.
- Always rate-limit OTP requests: at most 3 codes per phone per hour and 5 per day; at most 5 wrong verification attempts per code before it is invalidated.
- A logged-in customer may only ever see their own bookings — never another customer's, by id guessing or otherwise.
- ~~Guest booking must never be blocked behind login.~~ Superseded by CR-9 (client, 2026-11-11): booking needs a Google sign-in. ~~Booking needs a Google sign-in~~ (CR-13, 2026-11-13): sign-in is optional again; a guest booking has no email (`customer_email` NULL) and is never emailed.

Google sign-in, TrxID booking and email (CR-9):

- The email stored on a booking comes from the Google session (`session["customer"]`), never from a form field. No session = guest = no email (CR-13).
- A bKash TrxID can be used for one booking only; the database enforces it (unique index `uq_bookings_trx_id`). Never weaken that to an app-only check.
- Google redirect URIs are built from `SITE_URL`, never the request Host. `/auth/google` moves visitors to the `SITE_URL` host first (the OAuth state lives in that host's cookie).
- Booking emails are sent after the status change is committed and never undo it; a failure shows the owner "Resend email".
- `GOOGLE_CLIENT_SECRET` and `GMAIL_REFRESH_TOKEN` live only in env. Never log tokens, codes or Google response bodies; tests replace `services.google`'s network helpers and never call Google.
- The public template context (`inject_common`) is attached to the public and auth blueprints only. Never make it app-wide: the 404/500 pages must not read the database.

## Commands

Keep this list current when commands change.

```bash
# setup (macOS/Linux)
python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
# setup (Windows PowerShell)
python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements-dev.txt

flask --app app run --debug                      # run locally, then open /dev/wiring
pytest -q                                        # all tests; postgres tests skip without TEST_DATABASE_URL
pytest -q -m mariadb                             # needs a mysql+pymysql:// TEST_DATABASE_URL (throwaway DB: tests drop tables). Run before every deploy
pytest -q -m postgres                            # needs a postgresql:// TEST_DATABASE_URL; the URL's scheme picks which marker runs
flask --app app db migrate -m "message"          # autogenerate on SQLite; then hand-check uq_active_slot WHERE AND the MariaDB active_slot_key branch
flask --app app db upgrade                       # apply migrations
flask --app app db-check                         # connection, latency, tables, migration version
flask --app app seed-settings [--force]          # create turf_settings row from database/seed_data.py
flask --app app create-admin --username owner    # prints a generated password once
flask --app app reset-admin-password --username owner   # recovery: new generated password, signs out every session (the owner's own route: "Forgot username or password?" by email, M5.10)
flask --app app gmail-authorize                  # on your PC, once: sign in as tturfzone@gmail.com, prints GMAIL_REFRESH_TOKEN for cPanel (CR-9)
flask --app app fake-bookings --count 10         # fake rows, codes start with FK-
flask --app app fake-conflict-test               # proves the DB blocks double booking
flask --app app fake-clear                       # deletes FK- rows only
APP_ENV=production SECRET_KEY=... DATABASE_URL=... python scripts/serve_like_passenger.py   # cPanel simulation
python scripts/build_images.py                   # assets_raw/ originals -> static/ WebP + icons + og-image (needs Pillow, dev only)
```

Local MariaDB 11.4 for `-m mariadb` (portable, no service; database `tturf_test` on port 3307, URL in `.env`):

```bash
"$LOCALAPPDATA/mariadb-11.4.13-winx64/bin/mariadbd.exe" --datadir="$LOCALAPPDATA/mariadb-data-tturf" --port=3307 --bind-address=127.0.0.1 --console
```

Production has no SSH: deploy with the one-line cPanel Terminal commands in plan Appendix D.

## Gotchas learned so far

- SQLite ignores VARCHAR lengths; MariaDB (strict mode) and PostgreSQL enforce them. Run `pytest -m mariadb` before deploying model or seed changes.
- Fake data and the `/dev` pages exist only when `ENABLE_DEV_TOOLS` is true (development). Never enable it in production.
- `database/migrations/env.py` was edited to use `db.engine` (the generated `get_engine()` is deprecated). Keep it that way.

MariaDB (production, CR-4):

- No partial indexes. The one-booking-per-slot rule is the STORED generated column `active_slot_key` + unique `uq_active_slot_key` (D-42). Changing the active status list (e.g. CR-1's `PENDING_PAYMENT`) means a migration that updates BOTH the partial-index WHERE and the generated-column expression.
- Never let a migration put `uq_active_slot` on MariaDB: without its WHERE it becomes a plain unique (date, slot) index and a rejected booking would block its slot forever. The model uses `Index.ddl_if`, and `env.py` hides the hand-written rule from autogenerate.
- PyMySQL silently DROPS timezone offsets on write, without converting. Only write UTC (`models._time.utcnow()`) into DateTime columns, never `now_dhaka()`; values read back are naive UTC (D-44).
- A bulk `db.update(...)` whose WHERE compares a DateTime column needs `.execution_options(synchronize_session=False)`: the default tries the comparison in Python on loaded objects (naive vs aware -> TypeError). Keep such comparisons in SQL.
- Tables are forced to utf8mb4 (`extensions.MYSQL_TABLE_OPTIONS`) because a server default can be latin1. Keep table names lower-case (Linux MariaDB is case-sensitive).
- Test against MariaDB 11.4, not MySQL: generated-column behaviour differs.
- The host blocks outbound port 5432, so no external PostgreSQL (Neon) from production.
- cPanel Python App env vars reach the web process only. Terminal commands read the URL from `~/.tturfzone_db` (Appendix D).
