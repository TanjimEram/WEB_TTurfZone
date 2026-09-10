"""Admin authentication. One owner login, created with `flask create-admin`.

Session key `admin_id`; the session is cleared on both login and logout so a
fixated session id cannot survive a login.
"""
from functools import wraps

from flask import redirect, request, session, url_for

from extensions import db
from models import Admin

SESSION_KEY = "admin_id"


def verify_admin(username: str, password: str) -> Admin | None:
    """Return the Admin if the username + password match, else None."""
    admin = db.session.scalar(
        db.select(Admin).where(Admin.username == (username or "").strip())
    )
    if admin is not None and admin.check_password(password or ""):
        return admin
    return None


def login_admin(admin: Admin) -> None:
    session.clear()
    session[SESSION_KEY] = admin.id
    session.permanent = True


def logout_admin() -> None:
    session.clear()


def current_admin() -> Admin | None:
    admin_id = session.get(SESSION_KEY)
    if not admin_id:
        return None
    return db.session.get(Admin, admin_id)


def safe_next(target: str | None) -> str | None:
    """Only allow redirects back to an /admin path (no open redirects)."""
    if target and target.startswith("/admin") and "//" not in target[1:]:
        return target
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_admin() is None:
            return redirect(url_for("admin.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped
