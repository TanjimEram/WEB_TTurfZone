"""Admin authentication. One owner login, created with `flask create-admin`.

Session key `admin_id`; the session is cleared on both login and logout so a
fixated session id cannot survive a login.

Each session also carries a short fingerprint of the admin's password hash
(`admin_pw`, D-49). Changing the password - from Settings or with the
reset-admin-password command - changes the hash, so every other session stops
matching and is logged out on its next request. Same idea as Django's session auth hash.
"""
import hashlib
from functools import wraps

from flask import redirect, request, session, url_for

from extensions import db
from models import Admin

SESSION_KEY = "admin_id"
STAMP_KEY = "admin_pw"
MIN_PASSWORD_LENGTH = 12


class PasswordChangeError(Exception):
    """`.errors` maps field -> message (current_password / new_password / confirm_password)."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(errors.values()))
        self.errors = errors


def _password_stamp(admin: Admin) -> str:
    """Short fingerprint of the stored hash; changes whenever the password does."""
    return hashlib.sha256(admin.password_hash.encode()).hexdigest()[:16]


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
    session[STAMP_KEY] = _password_stamp(admin)
    session.permanent = True


def logout_admin() -> None:
    session.clear()


def current_admin() -> Admin | None:
    """The signed-in admin, or None. A session from before a password change is dropped."""
    admin_id = session.get(SESSION_KEY)
    if not admin_id:
        return None
    admin = db.session.get(Admin, admin_id)
    if admin is None or session.get(STAMP_KEY) != _password_stamp(admin):
        session.clear()
        return None
    return admin


def change_password(admin: Admin, current: str, new: str, confirm: str) -> None:
    """Change the signed-in admin's password. Raises PasswordChangeError, changing nothing.

    Every other session is logged out (D-49); this one stays signed in.
    """
    errors = {}
    if not admin.check_password(current or ""):
        errors["current_password"] = "Your current password is not right."
    if len(new or "") < MIN_PASSWORD_LENGTH:
        errors["new_password"] = f"Use at least {MIN_PASSWORD_LENGTH} characters."
    elif new == current:
        errors["new_password"] = "Choose a password different from the current one."
    if new != confirm:
        errors["confirm_password"] = "The two new passwords don't match."
    if errors:
        raise PasswordChangeError(errors)
    admin.set_password(new)
    db.session.commit()
    session[STAMP_KEY] = _password_stamp(admin)  # keep this browser signed in


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
