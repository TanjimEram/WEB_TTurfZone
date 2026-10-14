"""Owner-editable settings (M7.4, widened by CR-6 in M7.7, D-23).

The owner edits: contact numbers, address, opening hours, booking rules, the note on
the booking confirmation page, the booking window, the tagline and about text, the
12 slot start times, the default price and the price bands. Images, page layout and
design stay with the developer.

`parse_settings_form` only reads and validates; `save_owner_settings` also checks the
database (a slot-time change must not strand upcoming bookings) and writes.
"""
from datetime import time

from database.seed_data import DEFAULT_SETTINGS
from extensions import db
from models import Booking, TurfSettings
from services.bookings import BookingValidationError, normalize_phone
from services.pricing import price_table
from services.slots import SLOT_MINUTES, slot_label, slot_times, today_dhaka

DAY_OPTIONS = ("all", "weekday", "weekend")
MAX_BANDS = 10
SLOT_COUNT = 12
WINDOW_DAYS = (1, 60)
TEXT_LIMITS = {  # VARCHAR columns must fit (MariaDB strict mode rejects longer); TEXT kept readable
    "opening_hours_text": 160,
    "confirm_time_text": 160,
    "tagline": 160,
    "about_text": 1500,
    "booking_rules_text": 2000,
    "address": 500,
}


class SettingsValidationError(Exception):
    """`.errors` maps field -> message, same shape as BookingValidationError."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


def _phone(raw: str, field: str, errors: dict) -> str:
    """Empty stays empty (the site shows a TODO); anything else must be a BD mobile."""
    if not (raw or "").strip():
        return ""
    try:
        return normalize_phone(raw)
    except BookingValidationError:
        errors[field] = "Enter a valid Bangladeshi mobile number, e.g. 01712345678."
        return ""


def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def parse_slot_times(form, errors: dict) -> list[time] | None:
    """Fields slot-0 .. slot-11 ("HH:MM"). In order, at least SLOT_MINUTES apart (no overlap)."""
    try:
        times = [time.fromisoformat(form.get(f"slot-{i}", "").strip()).replace(second=0, microsecond=0)
                 for i in range(SLOT_COUNT)]
    except ValueError:
        errors["slot_times"] = "Enter all 12 start times, e.g. 06:00."
        return None
    for earlier, later in zip(times, times[1:]):
        if _minutes(later) - _minutes(earlier) < SLOT_MINUTES:
            errors["slot_times"] = (
                f"{slot_label(later)} starts less than {SLOT_MINUTES} minutes after {slot_label(earlier)}. "
                "Put the times in order, at least 90 minutes apart, so slots don't overlap."
            )
            return None
    return times


def parse_bands(form, slot_keys: list[str], errors: dict) -> list[dict]:
    """Rows band-<i>-label/-days/-price/-slots, in form order (the owner's order).

    Slot checkboxes carry the slot's position (0-11), so a band keeps its slots
    when the owner changes slot times in the same save. Fully blank rows are dropped.
    """
    bands = []
    for i in range(MAX_BANDS):
        label = form.get(f"band-{i}-label", "").strip()
        price = form.get(f"band-{i}-price", "").strip()
        picked = sorted({int(x) for x in form.getlist(f"band-{i}-slots") if x.isdigit() and int(x) < len(slot_keys)})
        if not (label or price or picked):
            continue
        days = form.get(f"band-{i}-days", "all")
        if not label or len(label) > 40:
            errors[f"band-{i}"] = "Give each price band a short name (up to 40 characters)."
        elif not price.isdigit():
            errors[f"band-{i}"] = "Price must be a whole number of taka, e.g. 4000."
        elif not picked:
            errors[f"band-{i}"] = "Tick at least one slot for this price."
        elif days not in DAY_OPTIONS:
            errors[f"band-{i}"] = "Pick which days this price applies to."
        else:
            bands.append({"label": label, "slots": [slot_keys[n] for n in picked],
                          "days": days, "price_bdt": int(price)})
    return bands


def parse_settings_form(form) -> dict:
    """Read and validate every field. Returns clean values; raises SettingsValidationError.

    Touches no database except reading the current slot times as a fallback.
    """
    errors: dict[str, str] = {}
    values = {
        "phone": _phone(form.get("phone", ""), "phone", errors),
        "whatsapp": _phone(form.get("whatsapp", ""), "whatsapp", errors),
    }
    for field, limit in TEXT_LIMITS.items():
        text = form.get(field, "").strip()
        if len(text) > limit:
            errors[field] = f"Keep this under {limit} characters (now {len(text)})."
        values[field] = text

    window = form.get("booking_window_days", "").strip()
    if not window.isdigit() or not WINDOW_DAYS[0] <= int(window) <= WINDOW_DAYS[1]:
        errors["booking_window_days"] = f"Enter a number of days from {WINDOW_DAYS[0]} to {WINDOW_DAYS[1]}."
    else:
        values["booking_window_days"] = int(window)

    default = form.get("default_price_bdt", "").strip()
    if not default.isdigit():
        errors["default_price_bdt"] = "Set a default price in whole taka. It covers any slot no band covers."
    else:
        values["default_price_bdt"] = int(default)

    times = parse_slot_times(form, errors)
    values["slot_times"] = times
    keys = [t.strftime("%H:%M") for t in (times or slot_times())]
    values["pricing"] = parse_bands(form, keys, errors)

    if errors:
        raise SettingsValidationError(errors)
    return values


def stranded_bookings(new_times: list[time]) -> list[Booking]:
    """Upcoming PENDING/CONFIRMED/BLOCKED rows at a start time that is not in `new_times`."""
    return db.session.scalars(
        db.select(Booking)
        .where(Booking.booking_date >= today_dhaka(),
               Booking.status.in_(Booking.ACTIVE_STATUSES),
               Booking.slot_time.not_in(new_times))
        .order_by(Booking.booking_date, Booking.slot_time)
    ).all()


def _stranded_message(rows: list[Booking]) -> str:
    shown = ", ".join(f"{b.booking_date:%a %d %b} {slot_label(b.slot_time)} ({b.booking_code})" for b in rows[:5])
    more = f" and {len(rows) - 5} more" if len(rows) > 5 else ""
    return (
        f"Slot times not changed: {len(rows)} upcoming booking(s) or block(s) are at a time you removed: "
        f"{shown}{more}. Cancel or unblock them first (Bookings or Calendar), or keep those times."
    )


def save_owner_settings(form) -> TurfSettings:
    """Validate the settings form and save it to the single turf_settings row.

    Raises SettingsValidationError and changes nothing if any field is invalid, or
    if new slot times would strand upcoming bookings at a removed time.
    """
    values = parse_settings_form(form)
    # ponytail: a booking made between this check and the commit could still land on a
    # removed time; it stays in the bookings list. A row lock would close the gap if needed.
    stranded = stranded_bookings(values["slot_times"])
    if stranded:
        raise SettingsValidationError({"slot_times": _stranded_message(stranded)})

    settings = TurfSettings.current()
    if settings is None:
        settings = TurfSettings(id=1, **DEFAULT_SETTINGS)
        db.session.add(settings)

    settings.phone = values["phone"]
    settings.whatsapp = "88" + values["whatsapp"] if values["whatsapp"] else ""  # wa.me wants 8801XXXXXXXXX
    for field in TEXT_LIMITS:
        setattr(settings, field, values[field])
    settings.booking_window_days = values["booking_window_days"]
    settings.default_price_bdt = values["default_price_bdt"]
    settings.slot_times = [t.strftime("%H:%M") for t in values["slot_times"]]
    settings.pricing = values["pricing"]
    db.session.commit()
    return settings


def preview_prices(form) -> dict:
    """What every slot would cost with the (unsaved) form, using the public resolver.

    Lenient: invalid bands are skipped and invalid slot times fall back to the
    current ones, so the preview keeps working while the owner is still typing.
    """
    errors: dict[str, str] = {}
    times = parse_slot_times(form, errors) or slot_times()
    keys = [t.strftime("%H:%M") for t in times]
    default = form.get("default_price_bdt", "").strip()
    draft = TurfSettings(  # transient: never added to the session
        pricing=parse_bands(form, keys, {}),
        default_price_bdt=int(default) if default.isdigit() else None,
    )
    return price_summary(price_table(draft, times))


def price_summary(table: dict) -> dict:
    """The price table plus counts the admin warns about."""
    rows = [row for kind in table.values() for row in kind]
    return {
        "table": table,
        "missing": sum(1 for r in rows if r["price_bdt"] is None),
        "defaulted": sum(1 for r in rows if r["band"] is None and r["price_bdt"] is not None),
    }


def current_price_summary() -> dict:
    """price_summary for the saved settings (dashboard warning, settings page on load)."""
    return price_summary(price_table(TurfSettings.current_or_default()))

