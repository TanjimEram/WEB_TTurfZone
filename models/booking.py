from extensions import db
from models._time import utcnow

ACTIVE_WHERE = "status IN ('PENDING', 'CONFIRMED', 'BLOCKED')"


class Booking(db.Model):
    """One row per booking request or owner block (plan D-04).

    A slot is taken while a row for that date+time is PENDING, CONFIRMED or BLOCKED.
    The partial unique index `uq_active_slot` makes the database enforce that rule,
    so two customers can never hold the same slot, even if they submit at the same moment.
    """

    __tablename__ = "bookings"

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    STATUSES = (PENDING, CONFIRMED, REJECTED, BLOCKED)
    ACTIVE_STATUSES = (PENDING, CONFIRMED, BLOCKED)

    id = db.Column(db.Integer, primary_key=True)
    booking_code = db.Column(db.String(12), unique=True, nullable=False)
    customer_name = db.Column(db.String(80))   # empty for BLOCKED rows
    phone = db.Column(db.String(14))           # normalized 01XXXXXXXXX; empty for BLOCKED rows
    booking_date = db.Column(db.Date, nullable=False)
    slot_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(10), nullable=False, default=PENDING)
    admin_note = db.Column(db.Text)            # block reason or rejection note
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        db.Index(
            "uq_active_slot", "booking_date", "slot_time", unique=True,
            postgresql_where=db.text(ACTIVE_WHERE),
            sqlite_where=db.text(ACTIVE_WHERE),
        ),
        db.Index("ix_bookings_status_date", "status", "booking_date"),
        db.CheckConstraint("status IN ('PENDING', 'CONFIRMED', 'REJECTED', 'BLOCKED')", name="booking_status"),
    )

    def __repr__(self) -> str:
        return f"<Booking {self.booking_code} {self.booking_date} {self.slot_time} {self.status}>"
