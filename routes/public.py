from datetime import date, time

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from extensions import db
from models import Booking, TurfSettings
from services.bookings import (
    BookingValidationError,
    SlotUnavailableError,
    create_booking_request,
)
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


def _render_booking_page(form, errors):
    """Render the booking page with the picker + details form (GET, or a failed POST)."""
    chips = _date_chips()
    valid = {chip["iso"] for chip in chips}
    preselect_date = form["date"] if form["date"] in valid else chips[0]["iso"]
    return render_template(
        "booking.html",
        settings=TurfSettings.current_or_default(),
        slot_labels=[slot_label(t) for t in SLOT_TIMES],
        date_chips=chips,
        preselect_date=preselect_date,
        preselect_slot=form["slot"],
        form=form,
        errors=errors,
    )


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
    """Booking page: date + slot picker (preselected from the query) and the details form."""
    form = {
        "name": "",
        "phone": "",
        "date": request.args.get("date", ""),
        "slot": request.args.get("slot", ""),
    }
    return _render_booking_page(form, errors={})


@bp.post("/book")
def book_submit():
    """Create a PENDING booking request. Server re-validates everything (D-04, D-05)."""
    form = {
        "name": request.form.get("name", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "date": request.form.get("date", ""),
        "slot": request.form.get("slot", ""),
    }

    try:
        booking_date = date.fromisoformat(form["date"])
        slot_time = time.fromisoformat(form["slot"])
    except ValueError:
        return _render_booking_page(form, {"slot": "Pick a date and time above."}), 400

    try:
        booking = create_booking_request(form["name"], form["phone"], booking_date, slot_time)
    except BookingValidationError as exc:
        return _render_booking_page(form, exc.errors), 400
    except SlotUnavailableError:
        return _render_booking_page(
            form, {"slot": "Sorry, that slot was just taken. Please pick another."}
        ), 409

    session["booking_request"] = booking.id
    return redirect(url_for("public.booking_success"))


@bp.get("/book/success")
def booking_success():
    """One-time confirmation, read from the session (D-11). Refresh -> home."""
    booking_id = session.pop("booking_request", None)
    booking = db.session.get(Booking, booking_id) if booking_id else None
    if booking is None:
        return redirect(url_for("public.home"))

    settings = TurfSettings.current_or_default()
    slot_display = slot_label(booking.slot_time)
    wa_text = (
        f"Hi, I requested a booking at {settings.turf_name or 'TTURFZONE'}. "
        f"Booking ID: {booking.booking_code}, "
        f"Date: {booking.booking_date:%d %b %Y}, Time: {slot_display}"
    )
    return render_template(
        "booking_success.html",
        settings=settings,
        booking=booking,
        slot_display=slot_display,
        date_display=f"{booking.booking_date:%A, %d %b %Y}",
        wa_text=wa_text,
    )


@bp.get("/healthz")
def healthz():
    """Uptime check. Must not touch the database (plan D-12)."""
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}
