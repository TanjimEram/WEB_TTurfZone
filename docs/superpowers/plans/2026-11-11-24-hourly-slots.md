# 24 Hourly Slots (Part A, CR-10) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 12 × 90-minute slots with 24 × 60-minute slots on an operating day that runs 06:00 → 06:00, grouped Morning / Afternoon / Night.

**Architecture:** Bookings keep their real calendar `booking_date` + `slot_time` (no schema change, D-42 untouched). A new "operating day" layer in `services/slots.py` maps the picker's day D to its 24 slots (06:00–23:00 on D, 00:00–05:00 on D+1). Pricing, the API, the admin calendar and the dashboard all take an operating day. `turf_settings.slot_times` is reused to mean "open hours" (subset of the 24; NULL = all).

**Tech Stack:** Flask, Flask-SQLAlchemy, Jinja, vanilla JS, pytest; MariaDB 11.4 (production), SQLite (tests).

**Spec:** `docs/superpowers/specs/2026-11-11-trxid-booking-24-slots-redesign-design.md` (Part A)

## Global Constraints

- `SLOT_MINUTES = 60`; slot starts 00:00 … 23:00; one hour per booking.
- Operating day D = 06:00 on D to 06:00 on D+1. Periods: Morning 06:00–11:00 starts (label "Morning", "6AM–12PM"), Afternoon 12:00–17:00 ("Afternoon", "12PM–6PM"), Night 18:00–23:00 then 00:00–05:00 ("Night", "6PM–6AM").
- Storage stays real calendar date + time. No migration in this part.
- All "today / past / window" logic in Asia/Dhaka via `now_dhaka()` (CLAUDE.md hard rule). Current operating day = date of (now_dhaka − 6 h).
- Pricing = three period prices `{"morning", "afternoon", "night"}` in `turf_settings.pricing`, same every day; no bands, no default price, no weekend split (supersedes D-46/D-47). A slot's price = its period's price (None until set).
- Date buttons show dates (`"Wed 11 Nov"`), never "Today"/"Tomorrow".
- `/api/availability` never returns customer data.
- No new dependency. Beginner-readable code, docstrings on service functions.
- Commits: `<type>(M4.8): ...`; PROJECT_PLAN.md updated in the final commit (CR-10, D-52, M4.8, session log, Resume here). Run `pytest -q` and `pytest -q -m mariadb` before the last commit.

## Review Focus

1. A customer at 03:00 Thursday opens the site: "Today" is Wednesday's operating day, and the Wed-night 03:00–05:00 slots (real date Thursday) are bookable; the 00:00–02:00 ones show past. (Task 1 test `test_current_operating_day_before_6am`, Task 4 test `test_booking_after_midnight_slot_uses_real_date`.)
2. The last day of the booking window: its night slots fall on the calendar day after the window but must still be bookable. (Task 1 `test_last_window_day_night_slots_are_bookable`.)
3. The 00:00–05:00 hours are Night prices, not Morning, even though they fall on the next calendar day; an unset period price shows "On request", never 0. (Task 2 `test_after_midnight_hours_use_night_price`, `test_unset_period_price_is_none`.)
4. `turf_settings.slot_times` still holding old 90-minute times (e.g. "07:30") from a dev database: non-hour values are ignored, and if none remain all 24 hours are open. (Task 1 `test_slot_times_ignores_non_hour_values`.)
5. The 23:00 slot ends at "12:00 AM" and the 00:00 slot belongs to the previous operating day in the admin calendar (block form posts the real date). (Task 3 `test_calendar_blocks_after_midnight_slot_on_real_date`.)

---

### Task 1: Operating-day slot model

**Files:**
- Modify: `services/slots.py`
- Test: `tests/test_slots.py`

**Interfaces:**
- Produces (used by every later task):
  - `SLOT_MINUTES = 60`, `DAY_START = time(6, 0)`
  - `ALL_HOURS: list[time]` = 24 starts in operating order 06:00 … 23:00, 00:00 … 05:00
  - `PERIODS: list[dict]` = `[{"key": "morning", "name": "Morning", "span": "6AM–12PM", "hours": [6..11]}, {"key": "afternoon", ... [12..17]}, {"key": "night", "name": "Night", "span": "6PM–6AM", "hours": [18..23, 0..5]}]`
  - `period_of(t: time) -> str` (period key)
  - `slot_times(settings=None) -> list[time]` open hours in operating order (NULL or no valid value → all 24)
  - `slot_date(day: date, t: time) -> date` real date of slot `t` in operating day `day` (`day` if t ≥ 06:00 else day + 1)
  - `operating_day(d: date, t: time) -> date` inverse (`d` if t ≥ 06:00 else d − 1)
  - `current_operating_day(now: datetime | None = None) -> date`
  - `is_within_window(day, now=None, days=None) -> bool` — `day` is an operating day; window starts at `current_operating_day(now)`
  - `is_valid_slot(t) -> bool` (open hour), `is_bookable(d, t, now=None, days=None) -> bool` — `d` real date; valid + start > now + `operating_day(d, t)` in window
  - `get_day_availability(day: date, now=None) -> list[dict]` — operating day; each `{"time", "label", "date" (ISO real date), "period", "state"}`
  - `slot_end(t)` now +60 min; `slot_label` unchanged

- [ ] **Step 1: Rewrite `tests/test_slots.py` for the new model.** Keep the existing Dhaka/label tests that still hold; replace 12-slot/90-minute assertions. New tests (frozen `now` = `datetime(2026, 11, 11, h, m, tzinfo=TZ)`, a Wednesday):

```python
def test_all_hours_in_operating_order():
    assert len(ALL_HOURS) == 24
    assert ALL_HOURS[0] == time(6) and ALL_HOURS[17] == time(23) and ALL_HOURS[18] == time(0) and ALL_HOURS[-1] == time(5)

def test_periods_cover_every_hour_once():
    hours = [h for p in PERIODS for h in p["hours"]]
    assert sorted(hours) == list(range(24))
    assert [p["key"] for p in PERIODS] == ["morning", "afternoon", "night"]
    assert period_of(time(11)) == "morning" and period_of(time(12)) == "afternoon" and period_of(time(2)) == "night"

def test_slot_date_and_operating_day_round_trip():
    wed = date(2026, 11, 11)
    assert slot_date(wed, time(23)) == wed and slot_date(wed, time(1)) == date(2026, 11, 12)
    assert operating_day(date(2026, 11, 12), time(1)) == wed and operating_day(wed, time(6)) == wed

def test_current_operating_day_before_6am():
    assert current_operating_day(datetime(2026, 11, 12, 3, 0, tzinfo=TZ)) == date(2026, 11, 11)
    assert current_operating_day(datetime(2026, 11, 12, 6, 0, tzinfo=TZ)) == date(2026, 11, 12)

def test_slot_end_is_one_hour_and_wraps():
    assert slot_end(time(23)) == time(0) and slot_label(slot_end(time(23))) == "12:00 AM"

def test_slot_times_default_is_all_24(app):
    assert slot_times() == ALL_HOURS

def test_slot_times_keeps_only_ticked_hours_in_operating_order(app):  # settings.slot_times = ["02:00", "07:00", "18:00"]
    assert slot_times(settings) == [time(7), time(18), time(2)]

def test_slot_times_ignores_non_hour_values(app):  # ["07:30", "09:00"] -> [time(9)]; ["07:30"] -> ALL_HOURS
    ...

def test_after_midnight_slot_bookable_until_it_starts(app):
    now = datetime(2026, 11, 12, 3, 0, tzinfo=TZ)
    assert not is_bookable(date(2026, 11, 12), time(2), now=now, days=14)
    assert is_bookable(date(2026, 11, 12), time(4), now=now, days=14)

def test_last_window_day_night_slots_are_bookable(app):
    now = datetime(2026, 11, 11, 12, 0, tzinfo=TZ)  # window days=2 -> Wed, Thu
    assert is_bookable(date(2026, 11, 13), time(1), now=now, days=2)      # Thu night, calendar Fri
    assert not is_bookable(date(2026, 11, 13), time(7), now=now, days=2)  # Fri day: outside

def test_closed_hour_is_not_bookable(app):  # slot_times = ["18:00"] -> 19:00 not bookable

def test_day_availability_spans_midnight(app):
    # PENDING at 2026-11-12 01:00, CONFIRMED at 2026-11-11 20:00, now = Wed 12:00
    slots = get_day_availability(date(2026, 11, 11), now=now)
    assert [s["time"] for s in slots][:2] == ["06:00", "07:00"] and len(slots) == 24
    by_time = {s["time"]: s for s in slots}
    assert by_time["01:00"]["date"] == "2026-11-12" and by_time["01:00"]["state"] == "pending"
    assert by_time["20:00"]["state"] == "booked" and by_time["20:00"]["period"] == "night"
    assert by_time["06:00"]["state"] == "past"
    assert set(slots[0]) == {"time", "label", "date", "period", "state"}
```

- [ ] **Step 2: Run** `pytest -q tests/test_slots.py` — Expected: FAIL (ImportError on `ALL_HOURS` / `PERIODS`).

- [ ] **Step 3: Implement the interfaces above in `services/slots.py`.** Delete the 12-entry `SLOT_TIMES` list (replace its imports elsewhere with `ALL_HOURS`). `get_day_availability` queries active bookings where `(date == day AND time >= 06:00) OR (date == day + 1 AND time < 06:00)` and keys them by `(date, time)`. `today_dhaka()` stays (calendar date) for anything that is not slot logic.

- [ ] **Step 4: Run** `pytest -q tests/test_slots.py` — Expected: PASS.

- [ ] **Step 5: Commit** `git commit -m "feat(M4.8): 24 hourly slots on a 6am-6am operating day"` (other suites may be red until Task 5; that's expected mid-plan, note it in the message body).

### Task 2: Three period prices and the availability API

**Files:**
- Modify: `services/pricing.py` (rewrite, much smaller), `routes/api.py`, `routes/public.py` (home passes the new price list)
- Test: `tests/test_pricing.py` (rewrite), `tests/test_availability_api.py`

**Interfaces:**
- Consumes: Task 1 `PERIODS`, `period_of`, `slot_times`.
- Produces:
  - `period_prices(settings) -> {"morning": int | None, "afternoon": int | None, "night": int | None}` (reads `settings.pricing` when it is a dict; anything else, e.g. the old band list, counts as unset)
  - `price_for(settings, t: time) -> int | None`
  - `prices_for_day(settings, day) -> {"HH:MM": int | None}` for the open hours (`day` kept in the signature for the API; it no longer changes the price)
  - `price_cards(settings) -> list[{"key", "name", "span", "price_bdt"}]` for the homepage, only periods that have an open hour; `[]` when no period has a price
  - Removed: `WEEKEND_DAYS`, `DAY_KINDS`, `day_kind`, `resolve`, `price_table`, `rundown`
  - API `GET /api/availability?date=D` (operating day) -> `{"date": D, "slots": [{time, label, date, period, state, price_bdt}]}`

- [ ] **Step 1: Rewrite `tests/test_pricing.py`:**

```python
def test_slot_price_is_its_period_price(app):   # pricing = {"morning": 1000, "afternoon": 1350, "night": 2000}
    assert price_for(settings, time(6)) == 1000 and price_for(settings, time(12)) == 1350 and price_for(settings, time(18)) == 2000
def test_after_midnight_hours_use_night_price(app):
    assert price_for(settings, time(0)) == 2000 and price_for(settings, time(5)) == 2000
def test_unset_period_price_is_none(app):        # pricing = {"night": 2000}
    assert price_for(settings, time(9)) is None
def test_old_band_list_counts_as_unset(app):     # pricing = [{"label": "x", "slots": ["06:00"], "days": "all", "price_bdt": 5}]
    assert period_prices(settings) == {"morning": None, "afternoon": None, "night": None}
def test_price_cards_skip_closed_periods(app):   # open hours only night -> one card
def test_price_cards_empty_without_prices(app):
```

API tests: 24 slots; keys exactly `{"time", "label", "date", "period", "state", "price_bdt"}`; the 01:00 slot's `date` is the next calendar day and its `price_bdt` is the night price; a booking on that real date at 01:00 shows `booked` under the previous operating day; still no names/phones; out-of-window operating day -> 400.

- [ ] **Step 2: Run** `pytest -q tests/test_pricing.py tests/test_availability_api.py` — Expected: FAIL.
- [ ] **Step 3: Implement** the interfaces. Homepage pricing section renders `price_cards` (one card per period: name, span, "60 min", price); keep current styles.
- [ ] **Step 4: Run** the two files — Expected: PASS.
- [ ] **Step 5: Commit** `feat(M4.8): three period prices, availability API per operating day`.

### Task 3: Owner settings, admin calendar and dashboard

**Files:**
- Modify: `services/settings.py`, `services/bookings.py` (`bookings_for_day`, `dashboard_summary`), `routes/admin.py`, `templates/admin/settings.html`, `templates/admin/calendar.html`, `templates/admin/dashboard.html` (only if it labels "today"), `static/js/admin_settings.js`
- Test: `tests/test_admin_routes.py`

**Interfaces:**
- Consumes: Task 1 (`ALL_HOURS`, `PERIODS`, `slot_times`, `slot_date`, `current_operating_day`), Task 2 `period_prices`.
- Produces:
  - Settings form fields: `open_hours` (checkboxes, value `"HH:MM"`, 24 grouped by `PERIODS`); `price-morning`, `price-afternoon`, `price-night` (whole taka, all three required, 1–100000; error keys `price-<key>`, message "Enter a price in whole taka."). Saved as `turf_settings.pricing = {"morning": n, "afternoon": n, "night": n}`. `parse_open_hours(form, errors) -> list[time] | None` (at least one ticked, else `errors["open_hours"] = "Tick at least one hour the ground is open."`). `stranded_bookings(new_times)` unchanged in meaning (upcoming active bookings at an hour being closed). Saved as `turf_settings.slot_times = ["HH:MM", ...]` in operating order, or `None` when all 24 ticked.
  - `bookings_for_day(day) -> list[Booking]`: active rows of operating day `day` (same date/time window as Task 1), ordered by operating order.
  - `dashboard_summary(today)`: `today` = `current_operating_day()`; "today's bookings" = that operating day.
  - Calendar: `GET /admin/calendar?date=D` (operating day, default `current_operating_day()`), slots grouped by period with headings; each slot's block form posts `date` = the slot's real date.
- Remove: `SLOT_COUNT`, `MAX_BANDS`, `DAY_OPTIONS`, `parse_slot_times`, `parse_bands`, `preview_prices`, the default-price field, the "Slot start times" and price-band sections, `POST /admin/settings/preview`, `templates/admin/_price_preview.html`, `static/js/admin_settings.js` and the no-JS "Preview prices" button. Dashboard price warning and `missing_content` ("Prices for every slot") now check that each period with an open hour has a price.

- [ ] **Step 1: Update/replace the M7.7 slot-time tests** with:

```python
def test_settings_closes_hours_and_public_grid_hides_them(as_admin): ...
    # post open_hours = 18:00..23:00 + 00:00..05:00 -> /api/availability shows 12 slots, all night
def test_closing_an_hour_with_an_upcoming_booking_is_refused(as_admin): ...
    # CONFIRMED tomorrow 07:00; post without 07:00 -> 400 naming the booking code; nothing saved
def test_no_open_hours_is_refused(as_admin): ...
def test_period_prices_save_and_show_on_the_grid(as_admin): ...
    # post 1000/1350/2000 -> pricing saved as the dict; /api/availability 07:00 = 1000, 01:00 = 2000
def test_missing_or_bad_period_price_is_refused(as_admin): ...
    # price-night blank or "abc" -> 400, error shown, nothing saved
def test_calendar_shows_24_slots_in_three_periods(as_admin): ...
    # "Morning", "Afternoon", "Night" headings; 24 .cal-slot
# Delete the M7.7 band / preview / default-price tests (feature removed).
def test_calendar_blocks_after_midnight_slot_on_real_date(as_admin): ...
    # calendar for Wed shows hidden date=Thu for the 01:00 block form; posting it blocks Thu 01:00
def test_dashboard_today_is_the_operating_day(as_admin, monkeypatch): ...
    # freeze now = Thu 02:00; a CONFIRMED Thu 01:00 booking is in today's list (Wed operating day)
```

- [ ] **Step 2: Run** `pytest -q tests/test_admin_routes.py` — Expected: the new tests FAIL.
- [ ] **Step 3: Implement** the interfaces above. Preview (`preview_prices`) uses the posted open hours (lenient fallback `slot_times()`).
- [ ] **Step 4: Run** `pytest -q tests/test_admin_routes.py` — Expected: PASS.
- [ ] **Step 5: Commit** `feat(M4.8): open hours, admin calendar and dashboard by operating day`.

### Task 4: Public picker and booking pages

**Files:**
- Modify: `routes/public.py` (`_date_chips`, `_render_booking_page`, `home`, context `slot_span`), `templates/partials/slot_picker.html`, `templates/booking.html` (only if it shows slot length), `static/js/booking.js`
- Test: `tests/test_public_routes.py`, `tests/test_home_page.py`, `tests/test_production_content.py`

**Interfaces:**
- Consumes: Task 1 (`current_operating_day`, `operating_day`, `PERIODS`, `slot_times`), Task 2 API shape.
- Produces:
  - Date chips start at `current_operating_day()`; every chip label is the date, `"%a %d %b"` (e.g. "Wed 11 Nov"); `date_chip_label(d)` loses its `today` parameter.
  - `/book?date=<real date>&slot=HH:MM` preselects chip `operating_day(date, slot)` and the slot.
  - `booking.js` renders slots under three period headings (Morning 6AM–12PM, Afternoon 12PM–6PM, Night 6PM–6AM), skips periods with no open hours, shows the slot's real date ("Thu 12 Nov") on cards whose `date` ≠ the chip's day, puts `slot.date` (not the chip date) into the form's hidden `date` and the Continue link, and computes the end time +60 min.
  - Homepage `slot_span` = first open slot start → last open slot end in operating order (all 24 → "06:00 AM" to "06:00 AM": render as "Open 24 hours" when all 24 are open).
  - Rest of the visual redesign is Part C; keep current styles.

- [ ] **Step 1: Tests.**

```python
def test_booking_after_midnight_slot_uses_real_date(client, monkeypatch):
    # freeze now = Wed 2026-11-11 12:00; POST /book date=2026-11-12 slot=01:00 -> 302, row stored on 2026-11-12 01:00
def test_book_page_preselects_operating_day_for_night_slot(client):
    # GET /book?date=<tomorrow>&slot=01:00 -> the chip for today's operating day is aria-pressed="true"
def test_date_chips_show_dates_not_today(client): ...  # GET /book: no "Today"/"Tomorrow"; first chip = current operating day as "%a %d %b"
def test_home_says_open_24_hours_when_all_hours_open(client): ...
def test_home_span_follows_open_hours(client): ...  # open 18:00..23:00 -> "06:00 PM" to "12:00 AM"
```

Update existing assertions that count 12 slots or mention 90 minutes.

- [ ] **Step 2: Run** `pytest -q tests/test_public_routes.py tests/test_home_page.py tests/test_production_content.py` — Expected: new tests FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the three files — Expected: PASS. Then browser check (dev server `tturfzone-dev`): at 360 px, three period headings, 24 cards, the 01:00 card shows tomorrow's date, select it → Continue → `/book` has hidden `date` = tomorrow; submit a booking; the slot shows booked; delete the test row afterwards.
- [ ] **Step 5: Commit** `feat(M4.8): picker grouped by period, night slots carry their real date`.

### Task 5: Whole suite, MariaDB, plan

**Files:**
- Modify: any remaining tests still assuming 12 × 90 (`tests/test_bookings.py`, `tests/test_fake_data.py`, `tests/test_cli.py` …), `services/fake_data.py` (picks from `slot_times()`), `docs/PROJECT_PLAN.md`, `CLAUDE.md` (§2 fixed-slots line is in the plan; CLAUDE.md "What this project is" unaffected)
- Test: full suite

- [ ] **Step 1: Run** `pytest -q`; fix every remaining failure that comes from the old slot model (update expectations, never weaken a rule). Expected end state: all pass except the 4 PostgreSQL skips.
- [ ] **Step 2: Start local MariaDB, run** `pytest -q -m mariadb` — Expected: 12 passed.
- [ ] **Step 3: Update `docs/PROJECT_PLAN.md`:** §2 slot line → 24 × 60 min, operating day; new D-52 (operating day, real-date storage, open hours replace D-48's editor, after-midnight cards show the real date, date buttons show dates) and D-53 (three period prices, every day); D-09/D-46/D-47/D-48 marked superseded by CR-10, C-31 obsolete; CR-9, CR-10, CR-11 rows from the spec (CR-10 Done, CR-9/CR-11 Approved, not built); new task M4.8 ticked with test counts; §5.2 `slot_times` meaning; §5.3 slots/pricing contracts; QA §B items for night slots; Known issues: past-day bookings at old 90-minute times no longer show in the calendar grid (still in the Bookings list); session log; Resume here (next: Part B after Google Cloud setup).
- [ ] **Step 4: Commit** `docs(M4.8): 24 hourly slots recorded (CR-10, D-52); CR-9 and CR-11 approved` and `git push`.
