"""Customer sign-in with Google (CR-9). Booking requires it; the owner's admin login is separate.

Session key `customer` = {"sub", "email", "name"}. Signing out removes only that key.
"""
import hmac
import secrets
from urllib.parse import urlparse

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from models import TurfSettings
from services import google

bp = Blueprint("auth", __name__)
SESSION_KEY = "customer"


def current_customer() -> dict | None:
    """The signed-in customer {"sub", "email", "name"}, or None."""
    return session.get(SESSION_KEY)


def safe_next(target: str | None) -> str:
    """Only same-site paths; anything else goes to the booking page."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("public.book")


@bp.app_context_processor
def inject_customer():
    return {"customer": current_customer()}


@bp.get("/login")
def login():
    """'Continue with Google'. Says so plainly if the Google client isn't configured."""
    return render_template("login.html", settings=TurfSettings.current_or_default(),
                           next_url=safe_next(request.args.get("next")),
                           google_ready=bool(current_app.config.get("GOOGLE_CLIENT_ID")))


@bp.get("/auth/google")
def google_start():
    """Start the Google round trip on the SITE_URL host.

    The state check lives in the session cookie, which belongs to one host. Google always
    returns to SITE_URL, so a visitor who started on www.tturfzone.com is first moved there.
    """
    site = urlparse(current_app.config["SITE_URL"])
    if request.host != site.netloc:
        return redirect(f"{site.scheme}://{site.netloc}{request.full_path.rstrip('?')}")
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    session["oauth_next"] = safe_next(request.args.get("next"))
    return redirect(google.sign_in_url(state))


@bp.get("/auth/google/callback")
def google_callback():
    expected = session.pop("oauth_state", None)
    next_url = safe_next(session.pop("oauth_next", None))
    if request.args.get("error"):
        flash("Google sign-in was cancelled.")
        return redirect(url_for("auth.login", next=next_url))
    state = request.args.get("state", "")
    try:
        if not expected or not hmac.compare_digest(state, expected):
            raise google.GoogleError("state mismatch")
        session[SESSION_KEY] = google.user_from_code(request.args.get("code", ""))
    except google.GoogleError as exc:
        current_app.logger.warning("Google sign-in failed: %s", exc)  # message never holds tokens
        flash("Couldn't sign in with Google. Please try again.")
        return redirect(url_for("auth.login", next=next_url))
    return redirect(next_url)


@bp.post("/auth/logout")
def logout():
    session.pop(SESSION_KEY, None)
    flash("Signed out.")
    return redirect(url_for("public.home"))
