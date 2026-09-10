"""Development-only diagnostics. Registered only when ENABLE_DEV_TOOLS is True (never in production)."""
from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from extensions import db
from models import Admin, Booking, TurfSettings
from services.db_health import check_database
from services.fake_data import clear_fake_data, make_fake_bookings, try_double_booking
from services.slots import get_day_availability, now_dhaka

bp = Blueprint("dev", __name__, url_prefix="/dev")


@bp.get("/wiring")
def wiring():
    health = check_database()
    counts = {}
    upcoming = []
    if health["ok"]:
        counts = {
            "admins": db.session.query(Admin).count(),
            "bookings": db.session.query(Booking).count(),
            "fake bookings": Booking.query.filter(Booking.booking_code.startswith("FK-")).count(),
            "settings row": "present" if TurfSettings.current() else "missing (run flask seed-settings)",
        }
        upcoming = Booking.query.order_by(Booking.booking_date, Booking.slot_time).limit(15).all()
    return render_template(
        "dev/wiring.html",
        health=health,
        counts=counts,
        upcoming=upcoming,
        env_name=current_app.config["ENV_NAME"],
        now=now_dhaka(),
        sample_day=upcoming[0].booking_date if upcoming else now_dhaka().date(),
        sample_slots=get_day_availability(upcoming[0].booking_date) if upcoming else [],
    )


@bp.post("/fake-bookings")
def fake_bookings():
    created = make_fake_bookings(count=10)
    flash(f"Created {len(created)} fake bookings.")
    return redirect(url_for("dev.wiring"))


@bp.post("/double-booking")
def double_booking():
    flash(try_double_booking()["message"])
    return redirect(url_for("dev.wiring"))


@bp.post("/clear-fake")
def clear_fake():
    flash(f"Deleted {clear_fake_data()} fake bookings.")
    return redirect(url_for("dev.wiring"))
