"""Slot helpers: 24 hourly slots on a 06:00 -> 06:00 operating day (CR-10, M4.8).

All time logic uses Asia/Dhaka; `now` is frozen here. Bookings keep their real
calendar date + time; the operating day only groups them for the picker.
"""
import datetime as dt

import pytest

from extensions import db
from models import Booking, TurfSettings
from services.slots import (
    ALL_HOURS,
    PERIODS,
    TZ,
    booking_window,
    current_operating_day,
    date_chip_label,
    get_day_availability,
    is_bookable,
    is_valid_slot,
    is_within_window,
    operating_day,
    period_of,
    slot_date,
    slot_end,
    slot_label,
    slot_times,
)

NOON = dt.datetime(2026, 9, 11, 12, 0, tzinfo=TZ)   # a Friday, midday Dhaka
TODAY = NOON.date()
WED = dt.date(2026, 11, 11)
THU = dt.date(2026, 11, 12)


@pytest.fixture(autouse=True)
def _app_context(app):
    """Open hours come from turf_settings, so these need the app + DB."""
    yield


def _open_hours(*keys):
    db.session.add(TurfSettings(id=1, turf_name="TTURFZONE", slot_times=list(keys)))
    db.session.commit()


def _book(day, t, status=Booking.CONFIRMED, code="TZ-TEST01"):
    db.session.add(Booking(booking_code=code, customer_name="Rafi", phone="01712345678",
                           booking_date=day, slot_time=t, status=status))
    db.session.commit()


# --- the 24 hours and their periods ----------------------------------------

def test_all_hours_in_operating_order():
    assert len(ALL_HOURS) == 24
    assert ALL_HOURS[0] == dt.time(6) and ALL_HOURS[17] == dt.time(23)
    assert ALL_HOURS[18] == dt.time(0) and ALL_HOURS[-1] == dt.time(5)


def test_periods_cover_every_hour_once():
    hours = [h for p in PERIODS for h in p["hours"]]
    assert sorted(hours) == list(range(24))
    assert [p["key"] for p in PERIODS] == ["morning", "afternoon", "night"]
    assert [p["span"] for p in PERIODS] == ["6AM–12PM", "12PM–6PM", "6PM–6AM"]
    assert period_of(dt.time(11)) == "morning"
    assert period_of(dt.time(12)) == "afternoon"
    assert period_of(dt.time(18)) == "night" and period_of(dt.time(2)) == "night"


def test_slot_date_and_operating_day_round_trip():
    assert slot_date(WED, dt.time(23)) == WED
    assert slot_date(WED, dt.time(1)) == THU
    assert operating_day(THU, dt.time(1)) == WED
    assert operating_day(WED, dt.time(6)) == WED


def test_current_operating_day_before_6am():
    assert current_operating_day(dt.datetime(2026, 11, 12, 3, 0, tzinfo=TZ)) == WED
    assert current_operating_day(dt.datetime(2026, 11, 12, 5, 59, tzinfo=TZ)) == WED
    assert current_operating_day(dt.datetime(2026, 11, 12, 6, 0, tzinfo=TZ)) == THU


def test_slot_end_is_one_hour_and_wraps():
    assert slot_end(dt.time(9)) == dt.time(10)
    assert slot_end(dt.time(23)) == dt.time(0)
    assert slot_label(slot_end(dt.time(23))) == "12:00 AM"


# --- open hours (turf_settings.slot_times) ---------------------------------

def test_slot_times_default_is_all_24():
    assert slot_times() == ALL_HOURS


def test_slot_times_keeps_only_ticked_hours_in_operating_order():
    _open_hours("02:00", "07:00", "18:00")
    assert slot_times() == [dt.time(7), dt.time(18), dt.time(2)]


def test_slot_times_ignores_non_hour_values():
    _open_hours("07:30", "09:00")
    assert slot_times() == [dt.time(9)]


def test_slot_times_with_only_old_90_minute_values_opens_all_hours():
    _open_hours("07:30", "22:30")
    assert slot_times() == ALL_HOURS


def test_closed_hour_is_not_valid_or_bookable():
    _open_hours("18:00")
    assert is_valid_slot(dt.time(18)) and not is_valid_slot(dt.time(19))
    assert not is_bookable(TODAY, dt.time(19), now=NOON, days=14)


def test_non_hour_time_is_not_valid():
    assert not is_valid_slot(dt.time(6, 30))


# --- booking window (operating days) ---------------------------------------

def test_booking_window_length_and_start():
    window = booking_window(TODAY, 14)
    assert window[0] == TODAY and len(window) == 14
    assert window[-1] == TODAY + dt.timedelta(days=13)


def test_booking_window_never_empty():
    assert booking_window(TODAY, 0) == [TODAY]


def test_date_chip_label_is_always_the_date():
    assert date_chip_label(TODAY) == "Fri 11 Sep"
    assert date_chip_label(dt.date(2026, 9, 18)) == "Fri 18 Sep"


def test_is_within_window_counts_operating_days():
    assert is_within_window(TODAY, now=NOON, days=14)
    assert not is_within_window(TODAY - dt.timedelta(days=1), now=NOON, days=14)
    assert is_within_window(TODAY + dt.timedelta(days=13), now=NOON, days=14)
    assert not is_within_window(TODAY + dt.timedelta(days=14), now=NOON, days=14)


def test_yesterdays_operating_day_is_in_window_before_6am():
    three_am_thu = dt.datetime(2026, 11, 12, 3, 0, tzinfo=TZ)
    assert is_within_window(WED, now=three_am_thu, days=14)


# --- is_bookable (real calendar date + hour) -------------------------------

def test_future_slot_today_is_bookable():
    assert is_bookable(TODAY, dt.time(18), now=NOON, days=14)


def test_past_slot_today_is_not_bookable():
    assert not is_bookable(TODAY, dt.time(9), now=NOON, days=14)


def test_slot_starting_exactly_now_is_not_bookable():
    assert not is_bookable(TODAY, dt.time(12), now=NOON, days=14)


def test_after_midnight_slot_bookable_until_it_starts():
    three_am_thu = dt.datetime(2026, 11, 12, 3, 0, tzinfo=TZ)
    assert not is_bookable(THU, dt.time(2), now=three_am_thu, days=14)
    assert is_bookable(THU, dt.time(4), now=three_am_thu, days=14)


def test_last_window_day_night_slots_are_bookable():
    noon_wed = dt.datetime(2026, 11, 11, 12, 0, tzinfo=TZ)   # window days=2 -> Wed, Thu
    fri = dt.date(2026, 11, 13)
    assert is_bookable(fri, dt.time(1), now=noon_wed, days=2)       # Thu night, calendar Fri
    assert not is_bookable(fri, dt.time(7), now=noon_wed, days=2)   # Fri day: outside


def test_slot_outside_window_is_not_bookable():
    assert not is_bookable(TODAY + dt.timedelta(days=60), dt.time(18), now=NOON, days=14)


# --- get_day_availability (one operating day) ------------------------------

def test_day_availability_spans_midnight():
    _book(THU, dt.time(1), status=Booking.PENDING, code="TZ-NIGHT1")
    _book(WED, dt.time(20), code="TZ-EVE001")
    _book(WED, dt.time(1), code="TZ-OTHER1")   # belongs to Tuesday's operating day
    noon_wed = dt.datetime(2026, 11, 11, 12, 0, tzinfo=TZ)

    slots = get_day_availability(WED, now=noon_wed)
    assert len(slots) == 24
    assert [s["time"] for s in slots][:2] == ["06:00", "07:00"]
    assert [s["time"] for s in slots][-1] == "05:00"
    assert set(slots[0]) == {"time", "label", "date", "period", "state"}

    by_time = {s["time"]: s for s in slots}
    assert by_time["01:00"]["date"] == "2026-11-12" and by_time["01:00"]["state"] == "pending"
    assert by_time["20:00"]["state"] == "booked" and by_time["20:00"]["period"] == "night"
    assert by_time["06:00"]["state"] == "past" and by_time["06:00"]["date"] == "2026-11-11"
    assert by_time["13:00"]["state"] == "available" and by_time["13:00"]["period"] == "afternoon"


def test_day_availability_only_open_hours():
    _open_hours("18:00", "02:00")
    slots = get_day_availability(TODAY + dt.timedelta(days=2), now=NOON)
    assert [s["time"] for s in slots] == ["18:00", "02:00"]
    assert {s["state"] for s in slots} == {"available"}
