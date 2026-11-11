"""Owner admin. Everything except /admin/login requires a session (login_required)."""
from datetime import date, time, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from extensions import db
from models import Booking, TurfSettings
from services.auth import (
    MIN_PASSWORD_LENGTH,
    PasswordChangeError,
    admin_from_reset_token,
    change_password,
    change_recovery_email,
    clear_login_failures,
    current_admin,
    is_locked_out,
    login_admin,
    login_required,
    logout_admin,
    record_login_failure,
    safe_next,
    send_reset_email,
    verify_admin,
)
from services.auth import reset_password as set_password_from_reset
from services.mailer import mail_configured
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
from services.pricing import period_prices
from services.settings import SettingsValidationError, missing_content, missing_prices, save_owner_settings
from services.slots import (
    ALL_HOURS,
    PERIODS,
    current_operating_day,
    get_day_availability,
    slot_label,
    slot_times,
)

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

    error, status = None, 200
    next_url = safe_next(request.values.get("next"))
    ip = request.remote_addr or "unknown"

    if request.method == "POST":
        if is_locked_out(ip):  # checked before the password, so a locked-out guess learns nothing
            error, status = ("Too many wrong sign-ins from this connection. Try again in 15 minutes, "
                             "or use \"Forgot username or password?\" below."), 429
        else:
            admin = verify_admin(request.form.get("username", ""), request.form.get("password", ""))
            if admin is not None:
                clear_login_failures(ip)
                login_admin(admin)
                return redirect(next_url or url_for("admin.dashboard"))
            record_login_failure(ip)
            error = "Invalid username or password."

    return render_template("admin/login.html", error=error, next_url=next_url or ""), status


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    """Email the username + a reset link to the recovery address (D-51). Same reply for any address."""
    message = None
    if request.method == "POST":
        if not mail_configured():
            message = ("Email sending is not set up on this site yet, so a reset link can't be sent. "
                       "Ask your developer to reset the password from the server.")
        else:
            send_reset_email(request.form.get("email", ""))
            message = "If that address is on file, a reset link is on its way. Check your spam folder too."
    return render_template("admin/forgot.html", message=message)


@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Choose a new password from an emailed link (D-51). Works once, for 30 minutes."""
    admin = admin_from_reset_token(token)
    if admin is None:
        return render_template("admin/reset.html", invalid=True, errors={},
                               min_password_length=MIN_PASSWORD_LENGTH), 400
    errors = {}
    if request.method == "POST":
        try:
            set_password_from_reset(admin, request.form.get("new_password", ""),
                                    request.form.get("confirm_password", ""))
        except PasswordChangeError as exc:
            errors = exc.errors
        else:
            clear_login_failures(request.remote_addr or "unknown")
            logout_admin()
            flash("Password changed. Sign in with your new password.")
            return redirect(url_for("admin.login"))
    return render_template("admin/reset.html", invalid=False, errors=errors,
                           min_password_length=MIN_PASSWORD_LENGTH), (400 if errors else 200)


@bp.post("/logout")
@login_required
def logout():
    logout_admin()
    flash("Signed out.")
    return redirect(url_for("admin.login"))


@bp.get("/")
@login_required
def dashboard():
    settings = TurfSettings.current_or_default()
    return render_template("admin/dashboard.html", summary=dashboard_summary(current_operating_day()),
                           missing_prices=missing_prices(settings), missing=missing_content(settings))


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
    """One operating day (06:00 to 06:00), its open hours grouped by period, with the
    actions the owner can take. After-midnight slots carry their real date (D-52)."""
    raw = request.args.get("date", "")
    try:
        day = date.fromisoformat(raw) if raw else current_operating_day()
    except ValueError:
        day = current_operating_day()

    rows = {(b.booking_date, b.slot_time): b for b in bookings_for_day(day)}
    slots = [{**s, "booking": rows.get((date.fromisoformat(s["date"]), time.fromisoformat(s["time"])))}
             for s in get_day_availability(day)]
    groups = [{"name": p["name"], "span": p["span"], "slots": [s for s in slots if s["period"] == p["key"]]}
              for p in PERIODS]

    return render_template(
        "admin/calendar.html",
        day=day,
        groups=[g for g in groups if g["slots"]],
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


TEXT_FIELDS = ("address", "opening_hours_text", "booking_rules_text", "confirm_time_text", "tagline", "about_text")


def _settings_form(settings) -> dict:
    """Current values for the settings form (GET)."""
    wa = settings.whatsapp or ""
    prices = period_prices(settings)
    values = {field: _clean(getattr(settings, field)) for field in TEXT_FIELDS}
    values.update({
        "phone": settings.phone or "",
        "whatsapp": wa[2:] if wa.startswith("88") else wa,
        "booking_window_days": str(settings.booking_window_days or 14),
        "open_hours": [t.strftime("%H:%M") for t in slot_times(settings)],
        "prices": {key: "" if price is None else str(price) for key, price in prices.items()},
    })
    return values


def _posted_form(form) -> dict:
    """What the owner just typed, so a failed save keeps their input."""
    values = {field: form.get(field, "") for field in TEXT_FIELDS + ("phone", "whatsapp", "booking_window_days")}
    values["open_hours"] = form.getlist("open_hours")
    values["prices"] = {p["key"]: form.get(f"price-{p['key']}", "") for p in PERIODS}
    return values


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Owner-editable business details, open hours and the three period prices (D-23, CR-10)."""
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
    return _render_settings(values, errors)


def _hour_groups() -> list[dict]:
    """The 24 hours grouped by period, for the open-hours checkboxes."""
    return [{**p, "slots": [{"key": t.strftime("%H:%M"), "label": slot_label(t)}
                            for t in ALL_HOURS if t.hour in p["hours"]]} for p in PERIODS]


def _render_settings(values, errors, pw_errors=None, email_value=None):
    """The settings page (business settings + password + recovery email forms). 400 when anything failed."""
    pw_errors = pw_errors or {}
    return render_template(
        "admin/settings.html", values=values, errors=errors, pw_errors=pw_errors,
        recovery_email=current_admin().email or "",
        email_value=(current_admin().email or "") if email_value is None else email_value,
        mail_ready=mail_configured(),
        hour_groups=_hour_groups(), periods=PERIODS,
        min_password_length=MIN_PASSWORD_LENGTH,
    ), (400 if errors or pw_errors else 200)


@bp.post("/settings/password")
@login_required
def settings_password():
    """Change the signed-in admin's password (D-49). Signs out every other session."""
    try:
        change_password(current_admin(), request.form.get("current_password", ""),
                        request.form.get("new_password", ""), request.form.get("confirm_password", ""))
    except PasswordChangeError as exc:
        return _render_settings(_settings_form(TurfSettings.current_or_default()), {}, pw_errors=exc.errors)
    flash("Password changed. Any other device signed in to the admin has been signed out.")
    return redirect(url_for("admin.settings") + "#password")


@bp.post("/settings/email")
@login_required
def settings_email():
    """Set the recovery address for "Forgot password" (D-51). Needs the current password."""
    email = request.form.get("email", "")
    try:
        change_recovery_email(current_admin(), request.form.get("current_password", ""), email)
    except PasswordChangeError as exc:
        return _render_settings(_settings_form(TurfSettings.current_or_default()), {},
                                pw_errors=exc.errors, email_value=email)
    flash("Recovery email saved. Password reset links will go there.")
    return redirect(url_for("admin.settings") + "#recovery")
