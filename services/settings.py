"""Owner-editable settings (M7.4, widened by CR-6 in M7.7, D-23).

The owner edits: contact numbers, address, opening hours, booking rules, the note on
the booking confirmation page, the booking window, the tagline and about text, which
of the 24 hours are open (CR-10) and the three period prices (D-53). Images, page
layout and design stay with the developer.

`parse_settings_form` only reads and validates; `save_owner_settings` also checks the
database (closing an hour must not strand upcoming bookings) and writes.
"""
from datetime import time

from database.seed_data import DEFAULT_SETTINGS
from extensions import db
from models import Booking, TurfSettings
from services.bookings import BookingValidationError, normalize_phone
from services.pricing import period_prices
from services.slots import ALL_HOURS, PERIODS, slot_label, slot_times, today_dhaka

WINDOW_DAYS = (1, 60)
MAX_PRICE_BDT = 100_000
ADVANCE_LIMITS = (1, 100_000)
WHY_MAX_POINTS = 8
WHY_TITLE_MAX = 60
WHY_TEXT_MAX = 200


def parse_why_points(raw: str, errors: dict) -> list[dict]:
    """'Why Choose Us' (CR-11): one point per line, 'Title: one line' or just 'Title'.

    Stored in turf_settings.facilities as [{"title", "text"}] (the column CR-5 left unused).
    Only what the owner writes is shown; nothing is filled in for them (never-invent rule).
    """
    points = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        title, _, text = line.partition(":")
        title, text = title.strip(), text.strip()
        if len(title) > WHY_TITLE_MAX or len(text) > WHY_TEXT_MAX:
            errors["why_text"] = (f"Keep each point short: a title up to {WHY_TITLE_MAX} characters, "
                                  f"then a colon and up to {WHY_TEXT_MAX} characters.")
        points.append({"title": title, "text": text})
    if len(points) > WHY_MAX_POINTS:
        errors["why_text"] = f"Add up to {WHY_MAX_POINTS} points (now {len(points)})."
    return points
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


def parse_open_hours(form, errors: dict) -> list[time] | None:
    """Checkboxes `open_hours` ("HH:00"), returned in operating order. At least one."""
    ticked = set(form.getlist("open_hours"))
    hours = [t for t in ALL_HOURS if t.strftime("%H:%M") in ticked]
    if not hours:
        errors["open_hours"] = "Tick at least one hour the ground is open."
        return None
    return hours


def parse_period_prices(form, errors: dict) -> dict:
    """Fields price-morning / price-afternoon / price-night: whole taka, all required."""
    prices = {}
    for period in PERIODS:
        field = f"price-{period['key']}"
        raw = form.get(field, "").strip()
        if not raw.isdigit() or not 1 <= int(raw) <= MAX_PRICE_BDT:
            errors[field] = "Enter a price in whole taka."
        else:
            prices[period["key"]] = int(raw)
    return prices


def parse_settings_form(form) -> dict:
    """Read and validate every field. Returns clean values; raises SettingsValidationError.

    Touches no database.
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

    values["bkash_number"] = _phone(form.get("bkash_number", ""), "bkash_number", errors)
    advance = form.get("advance_bdt", "").strip()
    if not advance.isdigit() or not ADVANCE_LIMITS[0] <= int(advance) <= ADVANCE_LIMITS[1]:
        errors["advance_bdt"] = "Enter the advance in whole taka, e.g. 500."
    else:
        values["advance_bdt"] = int(advance)
    values["why"] = parse_why_points(form.get("why_text", ""), errors)
    values["open_hours"] = parse_open_hours(form, errors)
    values["pricing"] = parse_period_prices(form, errors)

    if errors:
        raise SettingsValidationError(errors)
    return values


def stranded_bookings(new_times: list[time]) -> list[Booking]:
    """Upcoming PENDING/CONFIRMED/BLOCKED rows at an hour that is not in `new_times`."""
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
        f"Open hours not changed: {len(rows)} upcoming booking(s) or block(s) are at an hour you closed: "
        f"{shown}{more}. Cancel or unblock them first (Bookings or Calendar), or keep those hours open."
    )


def save_owner_settings(form) -> TurfSettings:
    """Validate the settings form and save it to the single turf_settings row.

    Raises SettingsValidationError and changes nothing if any field is invalid, or
    if closing an hour would strand upcoming bookings at it.
    """
    values = parse_settings_form(form)
    # ponytail: a booking made between this check and the commit could still land on a
    # closed hour; it stays in the bookings list. A row lock would close the gap if needed.
    stranded = stranded_bookings(values["open_hours"])
    if stranded:
        raise SettingsValidationError({"open_hours": _stranded_message(stranded)})

    settings = TurfSettings.current()
    if settings is None:
        settings = TurfSettings(id=1, **DEFAULT_SETTINGS)
        db.session.add(settings)

    settings.phone = values["phone"]
    settings.whatsapp = "88" + values["whatsapp"] if values["whatsapp"] else ""  # wa.me wants 8801XXXXXXXXX
    for field in TEXT_LIMITS:
        setattr(settings, field, values[field])
    settings.booking_window_days = values["booking_window_days"]
    settings.bkash_number = values["bkash_number"]
    settings.facilities = values["why"]
    settings.advance_bdt = values["advance_bdt"]
    hours = values["open_hours"]
    settings.slot_times = None if len(hours) == len(ALL_HOURS) else [t.strftime("%H:%M") for t in hours]
    settings.pricing = values["pricing"]
    db.session.commit()
    return settings


def why_points(settings) -> list[dict]:
    """The owner's Why Choose Us points, or [] (also for the old unused facilities shape)."""
    items = settings.facilities if isinstance(settings.facilities, list) else []
    return [i for i in items if isinstance(i, dict) and (i.get("title") or "").strip()]


def missing_prices(settings) -> int:
    """How many periods that have an open hour still have no price (dashboard warning)."""
    open_periods = {p["key"] for p in PERIODS if any(t.hour in p["hours"] for t in slot_times(settings))}
    prices = period_prices(settings)
    return sum(1 for key in open_periods if prices[key] is None)


def _filled(value) -> bool:
    return bool(value and "TODO" not in value and value.strip())


def missing_content(settings) -> list[dict]:
    """What the public site leaves out until it is filled in (production hides it, D-50).

    [{"label": "Prices", "where": "settings" | "developer"}, ...] in the order the owner should fix them.
    """
    checks = [
        ("Prices for every slot", "settings", not missing_prices(settings)),
        ("Phone number", "settings", _filled(settings.phone)),
        ("WhatsApp number", "settings", _filled(settings.whatsapp)),
        ("Address", "settings", _filled(settings.address)),
        ("Opening hours", "settings", _filled(settings.opening_hours_text)),
        ("Tagline", "settings", _filled(settings.tagline)),
        ("About the ground", "settings", _filled(settings.about_text)),
        ("Why Choose Us points", "settings", bool(why_points(settings))),
        ("Booking and cancellation rules", "settings", _filled(settings.booking_rules_text)),
        ("Google Maps location", "developer", _filled(settings.map_embed_url) or _filled(settings.map_link)),
        ("Customer reviews", "developer", bool(settings.reviews)),
    ]
    return [{"label": label, "where": where} for label, where, done in checks if not done]

