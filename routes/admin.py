"""Owner admin. Everything except /admin/login requires a session (login_required)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from services.auth import (
    current_admin,
    login_admin,
    login_required,
    logout_admin,
    safe_next,
    verify_admin,
)

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.context_processor
def inject_admin():
    return {"admin": current_admin()}


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
    return render_template("admin/dashboard.html")


# Filled in by M5.3 / M5.4. Present now so the admin nav resolves.
@bp.get("/bookings")
@login_required
def bookings():
    return render_template("admin/bookings.html")


@bp.get("/calendar")
@login_required
def calendar():
    return render_template("admin/calendar.html")
