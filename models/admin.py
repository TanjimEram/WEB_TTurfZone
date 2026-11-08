from werkzeug.security import check_password_hash, generate_password_hash

from extensions import MYSQL_TABLE_OPTIONS, db
from models._time import utcnow


class Admin(db.Model):
    """Owner login. Created with `flask create-admin`; there is no sign-up page."""

    __tablename__ = "admins"
    __table_args__ = MYSQL_TABLE_OPTIONS

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    email = db.Column(db.String(254), nullable=True)  # recovery address, lower-case (M5.10)
    reset_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)  # last reset email, UTC (throttle)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class LoginFailure(db.Model):
    """One wrong admin sign-in. Counted per address for the lockout (M5.10, D-51)."""

    __tablename__ = "login_failures"
    __table_args__ = (db.Index("ix_login_failures_ip_created", "ip", "created_at"), MYSQL_TABLE_OPTIONS)

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45), nullable=False)  # IPv6 fits in 45
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
