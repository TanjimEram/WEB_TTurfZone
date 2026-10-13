from sqlalchemy import DDL, event

from extensions import MYSQL_TABLE_OPTIONS, db
from models._time import utcnow

ACTIVE_WHERE = "status IN ('PENDING', 'CONFIRMED', 'BLOCKED')"

# MariaDB has no partial index (D-42). Instead a STORED generated column holds
# "YYYY-MM-DD HH:MM:SS" while the row is active and NULL otherwise, and a plain unique
# index on it allows many NULLs (released rows) but only one active row per slot.
# Same rule as uq_active_slot. If you change ACTIVE_WHERE, write a migration for both.
ACTIVE_SLOT_KEY = f"CASE WHEN {ACTIVE_WHERE} THEN CONCAT(booking_date, ' ', slot_time) END"
MARIADB = ("mysql", "mariadb")


class Booking(db.Model):
    """One row per booking request or owner block (plan D-04).

    A slot is taken while a row for that date+time is PENDING, CONFIRMED or BLOCKED.
    The database enforces that rule, so two customers can never hold the same slot,
    even if they submit at the same moment:
      PostgreSQL / SQLite: partial unique index `uq_active_slot` (WHERE ACTIVE_WHERE).
      MariaDB:             generated column `active_slot_key` + unique index
                           `uq_active_slot_key` (D-42). Not mapped here: the app never reads it.
    Timestamps are UTC; MariaDB stores them without an offset (see models/_time.py).
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
        ).ddl_if(dialect=("postgresql", "sqlite")),  # on MariaDB it would lose its WHERE
        db.Index("ix_bookings_status_date", "status", "booking_date"),
        db.CheckConstraint("status IN ('PENDING', 'CONFIRMED', 'REJECTED', 'BLOCKED')", name="booking_status"),
        MYSQL_TABLE_OPTIONS,
    )

    def __repr__(self) -> str:
        return f"<Booking {self.booking_code} {self.booking_date} {self.slot_time} {self.status}>"


# db.create_all() on MariaDB (tests): add the generated column + its unique index.
# Migrations do the same by hand (database/migrations/versions/13a53e9a5687_*).
event.listen(Booking.__table__, "after_create", DDL(
    f"ALTER TABLE bookings ADD COLUMN active_slot_key VARCHAR(20) AS ({ACTIVE_SLOT_KEY}) STORED, "
    "ADD UNIQUE INDEX uq_active_slot_key (active_slot_key)"
).execute_if(dialect=MARIADB))
