"""Owner-editable settings (M7.4, D-23): phone, WhatsApp, address, hours,
booking rules and prices. Photos, page text and layout stay with the developer.
"""
from database.seed_data import DEFAULT_SETTINGS
from extensions import db
from models import TurfSettings
from services.bookings import BookingValidationError, normalize_phone
from services.slots import SLOT_TIMES

SLOT_KEYS = [t.strftime("%H:%M") for t in SLOT_TIMES]
DAY_OPTIONS = ("all", "weekday", "weekend")
MAX_BANDS = 6


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


def _price_bands(form, errors: dict) -> list[dict]:
    """Rows band-<i>-label/-days/-price/-slots. Fully blank rows are dropped."""
    bands = []
    for i in range(MAX_BANDS):
        label = form.get(f"band-{i}-label", "").strip()
        price = form.get(f"band-{i}-price", "").strip()
        slots = [s for s in form.getlist(f"band-{i}-slots") if s in SLOT_KEYS]
        if not (label or price or slots):
            continue
        days = form.get(f"band-{i}-days", "all")
        if not label or len(label) > 40:
            errors[f"band-{i}"] = "Give each price band a short name (up to 40 characters)."
        elif not price.isdigit():
            errors[f"band-{i}"] = "Price must be a whole number of taka, e.g. 1500."
        elif not slots:
            errors[f"band-{i}"] = "Tick at least one slot for this price."
        elif days not in DAY_OPTIONS:
            errors[f"band-{i}"] = "Pick which days this price applies to."
        else:
            bands.append({"label": label, "slots": slots, "days": days, "price_bdt": int(price)})
    return bands


def save_owner_settings(form) -> TurfSettings:
    """Validate the settings form and save it to the single turf_settings row.

    `form` is a request.form-like mapping. Raises SettingsValidationError and
    changes nothing if any field is invalid.
    """
    errors: dict[str, str] = {}
    phone = _phone(form.get("phone", ""), "phone", errors)
    whatsapp = _phone(form.get("whatsapp", ""), "whatsapp", errors)
    hours = form.get("opening_hours_text", "").strip()
    if len(hours) > 160:  # VARCHAR(160): PostgreSQL rejects longer, SQLite would not
        errors["opening_hours_text"] = "Keep opening hours under 160 characters."
    pricing = _price_bands(form, errors)

    if errors:
        raise SettingsValidationError(errors)

    settings = TurfSettings.current()
    if settings is None:
        settings = TurfSettings(id=1, **DEFAULT_SETTINGS)
        db.session.add(settings)

    settings.phone = phone
    settings.whatsapp = "88" + whatsapp if whatsapp else ""  # wa.me wants 8801XXXXXXXXX
    settings.address = form.get("address", "").strip()
    settings.opening_hours_text = hours
    settings.booking_rules_text = form.get("booking_rules_text", "").strip()
    settings.pricing = pricing
    db.session.commit()
    return settings
