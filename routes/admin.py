"""Owner admin. Everything except /admin/login requires a session (login_required)."""
from datetime import date, time, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models import Booking, TurfSettings
from services.auth import (
    current_admin,
    login_admin,
    login_required,
    logout_admin,
    safe_next,
    verify_admin,
)
from services.bookings import (
    InvalidTransitionError,
    SlotUnavailableError,
    block_slot,
    bookings_for_day,
    confirm_booking,
    dashboard_summary,
    reject_booking,
    unblock_slot,
)
from services.settings import (
    DAY_OPTIONS,
    MAX_BANDS,
    SLOT_KEYS,
    SettingsValidationError,
    save_owner_settings,
)
from services.slots import SLOT_TIMES, get_day_availability, slot_label, today_dhaka

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _wa_number(phone: str) -> str:
    """01XXXXXXXXX -> 8801XXXXXXXXX for wa.me links."""
    phone = (phone or "").strip()
    return "88" + phone if phone.startswith("01") else phone


@bp.context_processor
def inject_admin():
    return {"admin": current_admin(), "slot_label": slot_label, "wa_number": _wa_number}


def _safe_back(default_endpoint: str) -> str:
    """A same-site /admin path to redirect back to after an action."""
    return safe_next(request.form.get("back")) or url_for(default_endpoint)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_admin() is not None:
        return redirect(url_for("admin.dashboard"))

    error = None
    next_url = safe_next(request.values.get("next"))

    if request.method == "POST":
        admin = verify_admin(request.form.get("username", ""), request.form.get("password", ""))
        if admin is not None:
            login_admin(admin)
            return redirect(next_url or url_for("admin.dashboard"))
        error = "Invalid username or password."

    return render_template("admin/login.html", error=error, next_url=next_url or "")


@bp.post("/logout")
@login_required
def logout():
    logout_admin()
    flash("Signed out.")
    return redirect(url_for("admin.login"))


@bp.get("/")
@login_required
def dashboard():
    return render_template("admin/dashboard.html", summary=dashboard_summary(today_dhaka()))


@bp.get("/bookings")
@login_required
def bookings():
    """Filterable list. ?date=YYYY-MM-DD (exact day) and ?status=PENDING|CONFIRMED|..."""
    query = db.select(Booking).order_by(Booking.booking_date.desc(), Booking.slot_time)

    day = request.args.get("date", "")
    try:
        day_value = date.fromisoformat(day) if day else None
    except ValueError:
        day_value = None
    if day_value:
        query = query.where(Booking.booking_date == day_value)

    status = request.args.get("status", "").upper()
    if status in Booking.STATUSES:
        query = query.where(Booking.status == status)

    rows = list(db.session.scalars(query.limit(300)))
    return render_template(
        "admin/bookings.html",
        rows=rows,
        statuses=Booking.STATUSES,
        filter_date=day if day_value else "",
        filter_status=status if status in Booking.STATUSES else "",
    )


@bp.post("/bookings/<int:booking_id>/confirm")
@login_required
def booking_confirm(booking_id):
    try:
        booking = confirm_booking(booking_id)
        flash(f"Confirmed {booking.booking_code}.")
    except InvalidTransitionError as exc:
        flash(str(exc))
    return redirect(_safe_back("admin.bookings"))


@bp.post("/bookings/<int:booking_id>/reject")
@login_required
def booking_reject(booking_id):
    note = request.form.get("note", "").strip() or None
    try:
        booking = reject_booking(booking_id, note=note)
        flash(f"{booking.booking_code} rejected. The slot is free again.")
    except InvalidTransitionError as exc:
        flash(str(exc))
    return redirect(_safe_back("admin.bookings"))


@bp.get("/calendar")
@login_required
def calendar():
    """One day, 12 slots, each with its state and the actions the owner can take."""
    raw = request.args.get("date", "")
    try:
        day = date.fromisoformat(raw) if raw else today_dhaka()
    except ValueError:
        day = today_dhaka()

    states = {s["time"]: s["state"] for s in get_day_availability(day)}
    rows = {b.slot_time: b for b in bookings_for_day(day)}

    slots = []
    for t in SLOT_TIMES:
        key = t.strftime("%H:%M")
        slots.append({
            "time": key,
            "label": slot_label(t),
            "state": states.get(key, "available"),
            "booking": rows.get(t),
        })

    return render_template(
        "admin/calendar.html",
        day=day,
        slots=slots,
        prev_day=(day - timedelta(days=1)).isoformat(),
        next_day=(day + timedelta(days=1)).isoformat(),
    )


@bp.post("/slots/block")
@login_required
def slot_block():
    try:
        booking_date = date.fromisoformat(request.form["date"])
        slot_time = time.fromisoformat(request.form["slot"])
    except (KeyError, ValueError):
        flash("Could not read that slot.")
        return redirect(_safe_back("admin.calendar"))
    try:
        block_slot(booking_date, slot_time, request.form.get("reason", ""))
        flash(f"Blocked {slot_label(slot_time)} on {booking_date:%d %b}.")
    except SlotUnavailableError:
        flash("That slot is already taken - cancel the booking first.")
    return redirect(_safe_back("admin.calendar"))


@bp.post("/slots/<int:booking_id>/unblock")
@login_required
def slot_unblock(booking_id):
    try:
        unblock_slot(booking_id)
        flash("Slot unblocked.")
    except InvalidTransitionError as exc:
        flash(str(exc))
    return redirect(_safe_back("admin.calendar"))


def _clean(value) -> str:
    """Owner text for a form field: '' while it is still a seed TODO placeholder."""
    value = (value or "").strip()
    return "" if "TODO" in value else value


def _settings_form(settings) -> dict:
    """Current values for the settings form (GET)."""
    wa = settings.whatsapp or ""
    bands = [
        {"label": b.get("label", ""), "days": b.get("days", "all"),
         "price": str(b.get("price_bdt", "")), "slots": b.get("slots", [])}
        for b in (settings.pricing or [])
    ]
    return {
        "phone": settings.phone or "",
        "whatsapp": wa[2:] if wa.startswith("88") else wa,
        "address": _clean(settings.address),
        "opening_hours_text": _clean(settings.opening_hours_text),
        "booking_rules_text": _clean(settings.booking_rules_text),
        "bands": bands,
    }


def _posted_form(form) -> dict:
    """What the owner just typed, so a failed save keeps their input."""
    bands = [
        {"label": form.get(f"band-{i}-label", ""), "days": form.get(f"band-{i}-days", "all"),
         "price": form.get(f"band-{i}-price", ""), "slots": form.getlist(f"band-{i}-slots")}
        for i in range(MAX_BANDS)
    ]
    values = {k: form.get(k, "") for k in ("phone", "whatsapp", "address", "opening_hours_text", "booking_rules_text")}
    values["bands"] = [b for b in bands if b["label"] or b["price"] or b["slots"]]
    return values


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Owner-editable business details (M7.4, D-23)."""
    errors = {}
    if request.method == "POST":
        try:
            save_owner_settings(request.form)
            flash("Settings saved. The public site shows them now.")
            return redirect(url_for("admin.settings"))
        except SettingsValidationError as exc:
            errors = exc.errors
            values = _posted_form(request.form)
    else:
        values = _settings_form(TurfSettings.current_or_default())

    # existing bands plus blank rows to add more, up to MAX_BANDS
    blanks = max(MAX_BANDS - len(values["bands"]), 0)
    values["bands"] += [{"label": "", "days": "all", "price": "", "slots": []}] * min(blanks, 2)
    return render_template(
        "admin/settings.html", values=values, errors=errors,
        slot_options=[(key, slot_label(t)) for key, t in zip(SLOT_KEYS, SLOT_TIMES)],
        day_options=DAY_OPTIONS,
    ), (400 if errors else 200)
