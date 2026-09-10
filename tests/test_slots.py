"""Slot helpers. M4.2 adds the booking-window helpers; M2.2 adds is_valid_slot / is_bookable."""
import datetime as dt

from services.slots import booking_window, date_chip_label


def test_booking_window_length_and_start():
    today = dt.date(2026, 9, 11)
    window = booking_window(today, 14)
    assert window[0] == today
    assert len(window) == 14
    assert window[-1] == today + dt.timedelta(days=13)


def test_booking_window_never_empty():
    today = dt.date(2026, 9, 11)
    assert booking_window(today, 0) == [today]


def test_date_chip_label():
    today = dt.date(2026, 9, 11)
    assert date_chip_label(today, today) == "Today"
    assert date_chip_label(today + dt.timedelta(days=1), today) == "Tomorrow"
    assert date_chip_label(dt.date(2026, 9, 18), today) == "Fri 18 Sep"
