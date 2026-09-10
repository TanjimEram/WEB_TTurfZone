"""Slot times and Dhaka time helpers.

M2.2 adds: is_valid_slot, is_bookable (past slots and booking-window rules).
`booking_window` is built in M4.2 (the date chips need it).
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from extensions import db
from models import Booking

TZ = ZoneInfo("Asia/Dhaka")
SLOT_MINUTES = 90
SLOT_TIMES = [
    time(6, 0), time(7, 30), time(9, 0), time(10, 30), time(12, 0), time(13, 30),
    time(15, 0), time(16, 30), time(18, 0), time(19, 30), time(21, 0), time(22, 30),
]

_STATE_FOR_STATUS = {
    Booking.PENDING: "pending",
    Booking.CONFIRMED: "booked",
    Booking.BLOCKED: "blocked",
}


def now_dhaka() -> datetime:
    return datetime.now(TZ)


def today_dhaka() -> date:
    return now_dhaka().date()


def slot_label(t: time) -> str:
    """time(13, 30) -> '01:30 PM'"""
    return t.strftime("%I:%M %p")


def booking_window(today: date, days: int) -> list[date]:
    """The bookable dates: `today` plus the next `days - 1` days.

    `days` comes from turf_settings.booking_window_days (default 14). A value
    below 1 still returns today so the picker is never empty.
    """
    return [today + timedelta(days=offset) for offset in range(max(days, 1))]


def date_chip_label(d: date, today: date) -> str:
    """Short label for a date chip: 'Today', 'Tomorrow', or 'Fri 12 Sep'."""
    if d == today:
        return "Today"
    if d == today + timedelta(days=1):
        return "Tomorrow"
    return d.strftime("%a %d %b")


def get_day_availability(day: date) -> list[dict]:
    """Public slot states for one day. Never includes customer data."""
    active = db.session.execute(
        db.select(Booking.slot_time, Booking.status)
        .where(Booking.booking_date == day, Booking.status.in_(Booking.ACTIVE_STATUSES))
    ).all()
    status_by_time = {slot: status for slot, status in active}

    return [
        {
            "time": t.strftime("%H:%M"),
            "label": slot_label(t),
            "state": _STATE_FOR_STATUS.get(status_by_time.get(t), "available"),
            "price_bdt": None,  # filled from turf_settings.pricing in M4
        }
        for t in SLOT_TIMES
    ]
