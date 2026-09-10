# TTURFZONE: instructions for Claude

@docs/PROJECT_PLAN.md

## What this project is

Website and slot-booking system for TTURFZONE, a single turf ground in Bangladesh.
Flask + Jinja templates + vanilla JS + PostgreSQL. Built by one developer with Claude Code in 2 days, then handed to the owner.

- MVP scope source of truth: `docs/brief/TTURFZONE_Claude_Code_Project_Brief.pdf`
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

## Commands

Keep this list current when commands change.

```bash
# setup (macOS/Linux)
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
# setup (Windows PowerShell)
python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt

flask --app app run --debug                      # run locally
pytest -q                                        # unit + route tests (SQLite)
TEST_DATABASE_URL=... pytest -q -m postgres      # concurrency test on a Postgres dev database
flask --app app db migrate -m "message"          # create migration (check the partial index WHERE clause is present)
flask --app app db upgrade                       # apply migrations
flask --app app create-admin                     # create owner login, prints generated password once
flask --app app seed-settings                    # insert/refresh turf_settings row from database/seed_data.py
flask --app app db-check                         # SELECT 1 against DATABASE_URL
```
