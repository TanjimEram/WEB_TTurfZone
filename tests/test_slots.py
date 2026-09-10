"""Slot helpers (M2.2 + M4.2). All time logic uses Asia/Dhaka; `now` is frozen here."""
import datetime as dt

from services.slots import (
    SLOT_TIMES,
    TZ,
    booking_window,
    date_chip_label,
    get_day_availability,
    is_bookable,
    is_valid_slot,
    is_within_window,
)

NOON = dt.datetime(2026, 9, 11, 12, 0, tzinfo=TZ)   # a Friday, midday Dhaka
TODAY = NOON.date()


# --- booking window (M4.2) -------------------------------------------------

def test_booking_window_length_and_start():
    window = booking_window(TODAY, 14)
    assert window[0] == TODAY
    assert len(window) == 14
    assert window[-1] == TODAY + dt.timedelta(days=13)


def test_booking_window_never_empty():
    assert booking_window(TODAY, 0) == [TODAY]


def test_date_chip_label():
    assert date_chip_label(TODAY, TODAY) == "Today"
    assert date_chip_label(TODAY + dt.timedelta(days=1), TODAY) == "Tomorrow"
    assert date_chip_label(dt.date(2026, 9, 18), TODAY) == "Fri 18 Sep"


# --- valid slots (M2.2) --------------------------------------------------

def test_is_valid_slot():
    assert all(is_valid_slot(t) for t in SLOT_TIMES)
    assert len(SLOT_TIMES) == 12
    assert not is_valid_slot(dt.time(6, 15))
    assert not is_valid_slot(dt.time(0, 0))


# --- is_within_window (M2.2) -------------------------------------------

def test_is_within_window():
    assert is_within_window(TODAY, now=NOON, days=14)
    assert not is_within_window(TODAY - dt.timedelta(days=1), now=NOON, days=14)
    assert is_within_window(TODAY + dt.timedelta(days=13), now=NOON, days=14)
    assert not is_within_window(TODAY + dt.timedelta(days=14), now=NOON, days=14)


# --- is_bookable (M2.2) ----------------------------------------------------

def test_future_slot_today_is_bookable():
    assert is_bookable(TODAY, dt.time(18, 0), now=NOON, days=14)


def test_past_slot_today_is_not_bookable():
    assert not is_bookable(TODAY, dt.time(9, 0), now=NOON, days=14)


def test_slot_starting_exactly_now_is_not_bookable():
    assert not is_bookable(TODAY, dt.time(12, 0), now=NOON, days=14)


def test_invalid_slot_time_is_not_bookable():
    assert not is_bookable(TODAY + dt.timedelta(days=1), dt.time(6, 15), now=NOON, days=14)


def test_slot_outside_window_is_not_bookable():
    assert not is_bookable(TODAY + dt.timedelta(days=60), dt.time(18, 0), now=NOON, days=14)


def test_slot_inside_window_is_bookable():
    assert is_bookable(TODAY + dt.timedelta(days=3), dt.time(6, 0), now=NOON, days=14)


# --- get_day_availability marks past slots (M2.2) -------------------------

def test_availability_marks_past_slots_today(app):
    slots = {s["time"]: s["state"] for s in get_day_availability(TODAY, now=NOON)}
    assert slots["09:00"] == "past"      # before noon
    assert slots["12:00"] == "past"      # starts exactly at noon
    assert slots["13:30"] == "available"  # after noon


def test_availability_future_day_has_no_past_slots(app):
    slots = get_day_availability(TODAY + dt.timedelta(days=2), now=NOON)
    assert {s["state"] for s in slots} == {"available"}
