from flask import Blueprint, render_template, request

from models import TurfSettings
from services.slots import (
    SLOT_TIMES,
    booking_window,
    date_chip_label,
    slot_label,
    today_dhaka,
)

bp = Blueprint("public", __name__)


@bp.context_processor
def inject_common():
    """Values every public template needs.

    now_year: footer copyright.
    wa_link:  wa.me deep link, or "" when the owner has not given a number (C-06).
    """
    settings = TurfSettings.current_or_default()
    digits = (settings.whatsapp or "").strip()
    return {
        "now_year": today_dhaka().year,
        "wa_link": f"https://wa.me/{digits}" if digits else "",
    }


def _date_chips():
    """Bookable dates for the slot picker: [{"iso", "label"}, ...] in Dhaka time (D-10)."""
    today = today_dhaka()
    days = TurfSettings.current_or_default().booking_window_days or 14
    return [
        {"iso": d.isoformat(), "label": date_chip_label(d, today)}
        for d in booking_window(today, days)
    ]


@bp.get("/")
def home():
    """Homepage. All business content comes from turf_settings (plan D-13)."""
    return render_template(
        "index.html",
        settings=TurfSettings.current_or_default(),
        slot_labels=[slot_label(t) for t in SLOT_TIMES],
        date_chips=_date_chips(),
    )


@bp.get("/book")
def book():
    """Booking page. M4.2 renders the date + slot picker (preselected from the
    query string). The details form and POST handler are added in M4.3."""
    chips = _date_chips()
    valid_dates = {c["iso"] for c in chips}
    preselect_date = request.args.get("date", "")
    if preselect_date not in valid_dates:
        preselect_date = chips[0]["iso"]
    return render_template(
        "booking.html",
        settings=TurfSettings.current_or_default(),
        slot_labels=[slot_label(t) for t in SLOT_TIMES],
        date_chips=chips,
        preselect_date=preselect_date,
        preselect_slot=request.args.get("slot", ""),
    )


@bp.get("/healthz")
def healthz():
    """Uptime check. Must not touch the database (plan D-12)."""
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}
