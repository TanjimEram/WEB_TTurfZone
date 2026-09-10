"""Slot times and Dhaka time helpers.

All "today" / "past slot" / booking-window logic uses Asia/Dhaka time
(CLAUDE.md hard rule), never the server clock. Pass a frozen `now` in tests.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from extensions import db
from models import Booking, TurfSettings

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


def is_valid_slot(t: time) -> bool:
    """True if `t` is one of the 12 fixed slot start times."""
    return t in SLOT_TIMES


def slot_start(d: date, t: time) -> datetime:
    """Dhaka-aware datetime for the start of a slot."""
    return datetime.combine(d, t, tzinfo=TZ)


def _as_dhaka(moment: datetime) -> datetime:
    """Treat a naive datetime as Dhaka time; convert an aware one to Dhaka."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=TZ)
    return moment.astimezone(TZ)


def _window_days(days: int | None) -> int:
    """Booking-window length: the given value, or turf_settings.booking_window_days."""
    if days is not None:
        return days
    settings = TurfSettings.current_or_default()
    return settings.booking_window_days or 14


def is_within_window(d: date, now: datetime | None = None, days: int | None = None) -> bool:
    """True if `d` is today or within the next `days - 1` days, in Dhaka time.

    `days` defaults to turf_settings.booking_window_days.
    """
    now = _as_dhaka(now or now_dhaka())
    return d in booking_window(now.date(), _window_days(days))


def is_bookable(d: date, t: time, now: datetime | None = None, days: int | None = None) -> bool:
    """True if a customer may still request slot `t` on date `d`:

    a real slot time, its start is in the future, and `d` is inside the window.
    `now` defaults to `now_dhaka()`; `days` to turf_settings.booking_window_days.
    """
    if not is_valid_slot(t):
        return False
    now = _as_dhaka(now or now_dhaka())
    if slot_start(d, t) <= now:
        return False
    return is_within_window(d, now=now, days=days)


def get_day_availability(day: date, now: datetime | None = None) -> list[dict]:
    """Public slot states for one day. Never includes customer data.

    A slot with no active booking whose start time has passed is `"past"`.
    """
    now = _as_dhaka(now or now_dhaka())
    active = db.session.execute(
        db.select(Booking.slot_time, Booking.status)
        .where(Booking.booking_date == day, Booking.status.in_(Booking.ACTIVE_STATUSES))
    ).all()
    status_by_time = {slot: status for slot, status in active}

    slots = []
    for t in SLOT_TIMES:
        status = status_by_time.get(t)
        if status:
            state = _STATE_FOR_STATUS.get(status, "booked")
        elif slot_start(day, t) <= now:
            state = "past"
        else:
            state = "available"
        slots.append(
            {
                "time": t.strftime("%H:%M"),
                "label": slot_label(t),
                "state": state,
                "price_bdt": None,  # filled from turf_settings.pricing in M4
            }
        )
    return slots
