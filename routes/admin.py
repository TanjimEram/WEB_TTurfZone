"""Owner admin. Everything except /admin/login requires a session (login_required)."""
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models import Booking
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
    confirm_booking,
    dashboard_summary,
    reject_booking,
)
from services.slots import slot_label, today_dhaka

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
    return render_template("admin/calendar.html")
