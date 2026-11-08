"""Admin authentication. One owner login, created with `flask create-admin`.

Session key `admin_id`; the session is cleared on both login and logout so a
fixated session id cannot survive a login.

Each session also carries a short fingerprint of the admin's password hash
(`admin_pw`, D-49). Changing the password - from Settings or with the
reset-admin-password command - changes the hash, so every other session stops
matching and is logged out on its next request. Same idea as Django's session auth hash.

Recovery and lockout (M5.10, D-51):
- 5 wrong sign-ins from one address lock that address out for 15 minutes (`login_failures`).
- "Forgot password" emails the username and a reset link to `admins.email`. The link is
  signed with SECRET_KEY, expires after 30 minutes, and carries the password fingerprint,
  so it stops working once the password changes (one use). One email per 5 minutes.
"""
import hashlib
import re
from datetime import timedelta
from functools import wraps

from flask import current_app, redirect, request, session, url_for
from itsdangerous import BadSignature, URLSafeTimedSerializer

from extensions import db
from models import Admin, LoginFailure
from models._time import utcnow
from services.mailer import send_email

SESSION_KEY = "admin_id"
STAMP_KEY = "admin_pw"
MIN_PASSWORD_LENGTH = 12
LOCKOUT_ATTEMPTS = 5
LOCKOUT_WINDOW = timedelta(minutes=15)
RESET_MAX_AGE_SECONDS = 30 * 60
RESET_EMAIL_EVERY = timedelta(minutes=5)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


def _new_password_errors(new: str, confirm: str) -> dict[str, str]:
    errors = {}
    if len(new or "") < MIN_PASSWORD_LENGTH:
        errors["new_password"] = f"Use at least {MIN_PASSWORD_LENGTH} characters."
    if new != confirm:
        errors["confirm_password"] = "The two new passwords don't match."
    return errors


def change_password(admin: Admin, current: str, new: str, confirm: str) -> None:
    """Change the signed-in admin's password. Raises PasswordChangeError, changing nothing.

    Every other session is logged out (D-49); this one stays signed in.
    """
    errors = _new_password_errors(new, confirm)
    if not admin.check_password(current or ""):
        errors["current_password"] = "Your current password is not right."
    if "new_password" not in errors and new == current:
        errors["new_password"] = "Choose a password different from the current one."
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


# --- lockout (D-51) ----------------------------------------------------------
# ponytail: per-address only; an attacker with many addresses is slowed, not stopped.
# The long generated password is what actually holds against that.

def is_locked_out(ip: str) -> bool:
    """True once `ip` has LOCKOUT_ATTEMPTS wrong sign-ins inside LOCKOUT_WINDOW."""
    since = utcnow() - LOCKOUT_WINDOW
    count = db.session.scalar(
        db.select(db.func.count()).select_from(LoginFailure)
        .where(LoginFailure.ip == ip, LoginFailure.created_at >= since)
    )
    return count >= LOCKOUT_ATTEMPTS


def record_login_failure(ip: str) -> None:
    """Remember one wrong sign-in; rows older than a day are deleted on the way."""
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.created_at < utcnow() - timedelta(days=1)))
    db.session.add(LoginFailure(ip=ip))
    db.session.commit()


def clear_login_failures(ip: str) -> None:
    db.session.execute(db.delete(LoginFailure).where(LoginFailure.ip == ip))
    db.session.commit()


# --- forgot password (D-51) --------------------------------------------------

def _reset_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.secret_key, salt="admin-password-reset")


def send_reset_email(email: str) -> None:
    """Email the username + a reset link if `email` belongs to an admin. Silent otherwise.

    Callers always show the same message, so the form never reveals which addresses exist.
    At most one email per RESET_EMAIL_EVERY; a failed send frees the slot for a retry.
    The link is built from SITE_URL, never from the request's Host header.
    """
    email = (email or "").strip().lower()
    admin = db.session.scalar(db.select(Admin).where(Admin.email == email)) if email else None
    if admin is None:
        return

    now = utcnow()
    claimed = db.session.execute(
        db.update(Admin)
        .where(Admin.id == admin.id,
               db.or_(Admin.reset_sent_at.is_(None), Admin.reset_sent_at < now - RESET_EMAIL_EVERY))
        .values(reset_sent_at=now)
        # compare in SQL only: MariaDB/SQLite read back naive UTC (D-44), so no Python-side sync
        .execution_options(synchronize_session=False)
    ).rowcount
    db.session.commit()
    if not claimed:
        return

    token = _reset_serializer().dumps({"id": admin.id, "pw": _password_stamp(admin)})
    link = current_app.config["SITE_URL"].rstrip("/") + url_for("admin.reset_password", token=token)
    body = (
        "Someone (hopefully you) asked to reset the TTURFZONE admin password.\n\n"
        f"Username: {admin.username}\n\n"
        "Choose a new password here. The link works once, for 30 minutes:\n"
        f"{link}\n\n"
        "If you didn't ask for this, ignore this email. Your password stays the same.\n"
    )
    try:
        send_email(admin.email, "TTURFZONE admin: reset your password", body)
    except Exception:
        current_app.logger.exception("Password reset email could not be sent")
        db.session.execute(db.update(Admin).where(Admin.id == admin.id).values(reset_sent_at=None)
                           .execution_options(synchronize_session=False))
        db.session.commit()


def admin_from_reset_token(token: str) -> Admin | None:
    """The admin a reset link belongs to, or None if it is forged, expired or already used."""
    try:
        data = _reset_serializer().loads(token, max_age=RESET_MAX_AGE_SECONDS)
    except BadSignature:  # includes SignatureExpired
        return None
    admin = db.session.get(Admin, data.get("id")) if isinstance(data, dict) else None
    if admin is None or data.get("pw") != _password_stamp(admin):
        return None
    return admin


def reset_password(admin: Admin, new: str, confirm: str) -> None:
    """Set a new password from a reset link. Raises PasswordChangeError. Signs out every session."""
    errors = _new_password_errors(new, confirm)
    if errors:
        raise PasswordChangeError(errors)
    admin.set_password(new)
    db.session.commit()


def change_recovery_email(admin: Admin, current: str, email: str) -> None:
    """Set the address reset links go to. Needs the current password. Raises PasswordChangeError."""
    email = (email or "").strip().lower()
    errors = {}
    if not admin.check_password(current or ""):
        errors["email_current_password"] = "Your current password is not right."
    if len(email) > 254 or not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address."
    if errors:
        raise PasswordChangeError(errors)
    admin.email = email
    db.session.commit()
