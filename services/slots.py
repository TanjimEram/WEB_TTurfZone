"""Slot times and Dhaka time helpers.

24 one-hour slots (CR-10). The picker shows an *operating day*: day D runs from
06:00 on D to 06:00 on D+1, in three periods (Morning, Afternoon, Night). A
booking still stores its real calendar date + time, so the 01:00 slot of
Wednesday's night is stored as Thursday 01:00 (D-52).

All "today" / "past slot" / booking-window logic uses Asia/Dhaka time
(CLAUDE.md hard rule), never the server clock. Pass a frozen `now` in tests.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from extensions import db
from models import Booking, TurfSettings

TZ = ZoneInfo("Asia/Dhaka")
SLOT_MINUTES = 60
DAY_START = time(6, 0)  # an operating day starts at 06:00 and ends at 06:00 the next day

# The 24 slot starts in operating order: 06:00 ... 23:00, then 00:00 ... 05:00.
ALL_HOURS = [time(hour % 24) for hour in range(DAY_START.hour, DAY_START.hour + 24)]

PERIODS = [
    {"key": "morning", "name": "Morning", "span": "6AM–12PM", "hours": list(range(6, 12))},
    {"key": "afternoon", "name": "Afternoon", "span": "12PM–6PM", "hours": list(range(12, 18))},
    {"key": "night", "name": "Night", "span": "6PM–6AM", "hours": list(range(18, 24)) + list(range(0, 6))},
]


def period_of(t: time) -> str:
    """The period key ("morning" / "afternoon" / "night") a slot start belongs to."""
    return next(p["key"] for p in PERIODS if t.hour in p["hours"])


def slot_times(settings=None) -> list[time]:
    """The open hours, in operating order.

    turf_settings.slot_times lists the hours the owner offers ("HH:00"); NULL means
    all 24. Anything that isn't one of the 24 hourly starts (e.g. an old 90-minute
    time like "07:30") is ignored, and if nothing valid is left all 24 are open.
    """
    settings = settings or TurfSettings.current_or_default()
    saved = set(settings.slot_times or [])
    open_hours = [t for t in ALL_HOURS if t.strftime("%H:%M") in saved]
    return open_hours or list(ALL_HOURS)


def slot_date(day: date, t: time) -> date:
    """Real calendar date of slot `t` in operating day `day` (after midnight = the next day)."""
    return day if t >= DAY_START else day + timedelta(days=1)


def operating_day(d: date, t: time) -> date:
    """The operating day a slot on real date `d` at `t` belongs to (inverse of slot_date)."""
    return d if t >= DAY_START else d - timedelta(days=1)


def current_operating_day(now: datetime | None = None) -> date:
    """The operating day in progress: before 06:00 it is still yesterday's."""
    now = _as_dhaka(now or now_dhaka())
    return (now - timedelta(hours=DAY_START.hour)).date()


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


def slot_end(t: time) -> time:
    """Start + SLOT_MINUTES, e.g. 22:30 -> 00:00."""
    return (datetime.combine(date.min, t) + timedelta(minutes=SLOT_MINUTES)).time()


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
    """True if `t` is one of the open hourly slot starts."""
    return t in slot_times()


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


def is_within_window(day: date, now: datetime | None = None, days: int | None = None) -> bool:
    """True if operating day `day` is the current one or within the next `days - 1`.

    `days` defaults to turf_settings.booking_window_days.
    """
    return day in booking_window(current_operating_day(now), _window_days(days))


def is_bookable(d: date, t: time, now: datetime | None = None, days: int | None = None) -> bool:
    """True if a customer may still request slot `t` on real calendar date `d`:

    an open hour, its start is in the future, and its operating day is inside the window.
    `now` defaults to `now_dhaka()`; `days` to turf_settings.booking_window_days.
    """
    if not is_valid_slot(t):
        return False
    now = _as_dhaka(now or now_dhaka())
    if slot_start(d, t) <= now:
        return False
    return is_within_window(operating_day(d, t), now=now, days=days)


def get_day_availability(day: date, now: datetime | None = None) -> list[dict]:
    """Public slot states for operating day `day`, in operating order:

        [{"time": "01:00", "label": "01:00 AM", "date": "2026-11-12", "period": "night", "state": ...}]

    `date` is the slot's real calendar date. Never includes customer data; prices
    are added by the API (services/pricing.py). A free slot whose start has passed
    is "past".
    """
    now = _as_dhaka(now or now_dhaka())
    next_day = day + timedelta(days=1)
    active = db.session.execute(
        db.select(Booking.booking_date, Booking.slot_time, Booking.status).where(
            Booking.status.in_(Booking.ACTIVE_STATUSES),
            db.or_(
                db.and_(Booking.booking_date == day, Booking.slot_time >= DAY_START),
                db.and_(Booking.booking_date == next_day, Booking.slot_time < DAY_START),
            ),
        )
    ).all()
    status_at = {(d, t): status for d, t, status in active}

    slots = []
    for t in slot_times():
        real_date = slot_date(day, t)
        status = status_at.get((real_date, t))
        if status:
            state = _STATE_FOR_STATUS.get(status, "booked")
        elif slot_start(real_date, t) <= now:
            state = "past"
        else:
            state = "available"
        slots.append({"time": t.strftime("%H:%M"), "label": slot_label(t), "date": real_date.isoformat(),
                      "period": period_of(t), "state": state})
    return slots
