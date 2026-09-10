# TTURFZONE: instructions for Claude

@docs/PROJECT_PLAN.md

## What this project is

Website and self-sufficient slot-booking system for TTURFZONE, a single turf ground in Bangladesh.
Flask + Jinja templates + vanilla JS + PostgreSQL. Built by one developer with Claude Code, then handed to the owner.

The owner should not have to confirm each online booking by hand. The site:
- takes payment online (bKash direct gateway, verified server-to-server), then confirms the booking automatically;
- holds a slot only while the customer is paying (`PENDING_PAYMENT`, expires after `HOLD_MINUTES`);
- sends notifications: SMS + email to the customer, SMS + email alert to the owner, and a reminder before the slot;
- runs scheduled jobs (cPanel cron, once a minute) to expire holds, send queued notifications and send reminders.

Manual fallback: config flag `PAYMENTS_ENABLED`. When `false` (the launch state, until the bKash merchant account is
approved) the site runs the original owner-confirmation flow: a booking is a `PENDING` request the owner confirms or rejects.
When `true`, online bookings go through payment holds and auto-confirm. See CR-1 in the plan.

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
- Never invent business information (prices, facilities, reviews, hours, address). Use `TODO(owner): ...` placeholders and make sure each one appears in the Client inputs table.
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
- Double booking is prevented by the database (partial unique index, see plan section 5). Frontend checks are only for UX.
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

## Commands

Keep this list current when commands change.

```bash
# setup (macOS/Linux)
python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
# setup (Windows PowerShell)
python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements-dev.txt

flask --app app run --debug                      # run locally, then open /dev/wiring
pytest -q                                        # all tests; postgres tests skip without TEST_DATABASE_URL
pytest -q -m postgres                            # needs TEST_DATABASE_URL (throwaway DB: tests drop tables)
flask --app app db migrate -m "message"          # new migration: open it and check the uq_active_slot WHERE clause
flask --app app db upgrade                       # apply migrations
flask --app app db-check                         # connection, latency, tables, migration version
flask --app app seed-settings [--force]          # create turf_settings row from database/seed_data.py
flask --app app create-admin --username owner    # prints a generated password once
flask --app app fake-bookings --count 10         # fake rows, codes start with FK-
flask --app app fake-conflict-test               # proves the DB blocks double booking
flask --app app fake-clear                       # deletes FK- rows only
APP_ENV=production SECRET_KEY=... DATABASE_URL=... python scripts/serve_like_passenger.py   # cPanel simulation
```

## Gotchas learned so far

- SQLite ignores VARCHAR lengths; PostgreSQL enforces them. Run `pytest -m postgres` before deploying model or seed changes.
- Fake data and the `/dev` pages exist only when `ENABLE_DEV_TOOLS` is true (development). Never enable it in production.
- `database/migrations/env.py` was edited to use `db.engine` (the generated `get_engine()` is deprecated). Keep it that way.
