"""Booking operations.

`save_booking` is the database-safe insert/update everything commits through.
M2.3 adds the request/owner actions: create_booking_request, confirm_booking,
reject_booking, block_slot, unblock_slot, plus phone normalisation.
"""
import re
import secrets
from datetime import date, timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Booking
from services.slots import DAY_START, is_bookable

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, easy to read out on the phone


class BookingValidationError(Exception):
    """One or more submitted fields are invalid. `.errors` maps field -> message."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


class SlotUnavailableError(Exception):
    """The slot is already pending, confirmed or blocked."""


class InvalidTransitionError(Exception):
    """The booking is not in a status this action allows."""


# --------------------------------------------------------------- codes / save

def generate_booking_code(prefix: str = "TZ") -> str:
    """Return a code like 'TZ-7K3M9Q'."""
    return prefix + "-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))


def save_booking(booking: Booking) -> Booking:
    """Insert or update a booking and commit.

    Raises SlotUnavailableError when the database's uq_active_slot index
    rejects it, which means someone else already holds that slot.
    """
    db.session.add(booking)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        if _is_slot_conflict(exc):
            raise SlotUnavailableError("That slot was just taken.") from exc
        raise
    return booking


def _is_slot_conflict(exc: IntegrityError) -> bool:
    """True when the IntegrityError is the one-active-booking-per-slot rule, per engine:

    PostgreSQL: 'duplicate key value violates unique constraint "uq_active_slot"'
    MariaDB:    (1062, "Duplicate entry '2026-10-14 18:00:00' for key 'uq_active_slot_key'")
    SQLite:     'UNIQUE constraint failed: bookings.booking_date, bookings.slot_time'
    A clash on booking_code ('uq_bookings_booking_code') is NOT a slot conflict.
    """
    message = str(exc.orig)
    return (
        "uq_active_slot" in message  # PostgreSQL, and MariaDB's uq_active_slot_key
        or "bookings.booking_date, bookings.slot_time" in message
    )


# --------------------------------------------------------------- validation

def normalize_phone(raw: str) -> str:
    """Accept '01XXXXXXXXX', '+8801XXXXXXXXX' or '8801XXXXXXXXX' -> '01XXXXXXXXX'.

    Raises BookingValidationError if it is not a valid Bangladeshi mobile number.
    """
    digits = re.sub(r"[\s\-()]", "", raw or "")
    if digits.startswith("+880"):
        digits = "0" + digits[4:]
    elif digits.startswith("880"):
        digits = "0" + digits[3:]
    if not re.fullmatch(r"01[3-9]\d{8}", digits):
        raise BookingValidationError({"phone": "Enter a valid Bangladeshi mobile number, e.g. 01712345678."})
    return digits


ADVANCE_DEFAULT_BDT = 500  # C-22; the owner can change it in Settings (turf_settings.advance_bdt)
TRX_ID_RE = re.compile(r"^[A-Z0-9]{8,12}$")  # bKash TrxIDs are 10 letters/digits; allow a little slack


def normalize_trx_id(raw: str) -> str:
    """' 8n7a6d5e4f ' -> '8N7A6D5E4F'. Raises BookingValidationError unless 8-12 letters/digits."""
    trx = (raw or "").strip().upper()
    if not TRX_ID_RE.match(trx):
        raise BookingValidationError(
            {"trx_id": "Enter the bKash transaction ID (TrxID) from your payment message."})
    return trx


def _trx_id_taken(trx_id: str) -> bool:
    return db.session.scalar(db.select(Booking.id).where(Booking.trx_id == trx_id).limit(1)) is not None


def _clean_name(raw: str) -> str:
    name = (raw or "").strip()
    if not (1 <= len(name) <= 80):
        raise BookingValidationError({"name": "Enter your name (up to 80 characters)."})
    return name


# --------------------------------------------------------------- actions

def create_booking_request(name: str, phone: str, booking_date, slot_time, *,
                           email: str, payer_number: str, trx_id: str) -> Booking:
    """Validate and insert a booking that waits for the owner to check its bKash payment (CR-9).

    The customer has paid the advance to the merchant number and gives the TrxID and the
    number they paid from. The booking is PENDING, which already holds the slot in the
    database rule (D-42), until the owner confirms or rejects it. `email` comes from the
    Google sign-in, never from the form. Every TrxID can be used once (unique index).

    Raises BookingValidationError (errors keyed name / phone / payer_number / trx_id / slot)
    or SlotUnavailableError (slot taken between the page load and submit).
    """
    errors: dict[str, str] = {}
    clean = {}
    for key, check, raw in (("name", _clean_name, name), ("phone", normalize_phone, phone),
                            ("payer_number", normalize_phone, payer_number), ("trx_id", normalize_trx_id, trx_id)):
        try:
            clean[key] = check(raw)
        except BookingValidationError as exc:
            errors[key] = exc.errors.get(key) or next(iter(exc.errors.values()))

    if not is_bookable(booking_date, slot_time):
        errors["slot"] = "That slot can no longer be booked."
    if "trx_id" not in errors and _trx_id_taken(clean["trx_id"]):
        errors["trx_id"] = TRX_USED
    if errors:
        raise BookingValidationError(errors)

    if current_app.config.get("PAYMENTS_ENABLED"):
        # ponytail: a bKash gateway (M10) would verify payments itself; not built.
        # Fail loudly rather than insert a booking under the wrong flow.
        raise NotImplementedError("PAYMENTS_ENABLED=true needs the bKash gateway (M10, not built).")

    try:
        return save_booking(Booking(
            booking_code=generate_booking_code(),
            customer_name=clean["name"],
            phone=clean["phone"],
            booking_date=booking_date,
            slot_time=slot_time,
            status=Booking.PENDING,
            customer_email=(email or "").strip().lower(),
            payer_number=clean["payer_number"],
            trx_id=clean["trx_id"],
        ))
    except IntegrityError as exc:
        if "trx_id" in str(exc.orig):  # another request used this TrxID a moment ago
            raise BookingValidationError({"trx_id": TRX_USED}) from exc
        raise


TRX_USED = "This transaction ID has already been used."


def _get(booking_id: int) -> Booking:
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        raise InvalidTransitionError(f"Booking {booking_id} does not exist.")
    return booking


def confirm_booking(booking_id: int) -> Booking:
    """PENDING -> CONFIRMED. Raises InvalidTransitionError from any other status."""
    booking = _get(booking_id)
    if booking.status != Booking.PENDING:
        raise InvalidTransitionError(f"Cannot confirm a {booking.status} booking.")
    booking.status = Booking.CONFIRMED
    booking.email_sent_at = None  # the customer hasn't heard about this status yet
    return save_booking(booking)


CANCELLED_NOTE = "Cancelled by the ground."


def reject_booking(booking_id: int, note: str | None = None) -> Booking:
    """PENDING or CONFIRMED -> REJECTED (frees the slot). Used for 'reject' and 'cancel'.

    `note` is the owner's reason; the customer's email quotes it. Cancelling a CONFIRMED
    booking without a reason records CANCELLED_NOTE, so the email says it was cancelled.
    """
    booking = _get(booking_id)
    if booking.status not in (Booking.PENDING, Booking.CONFIRMED):
        raise InvalidTransitionError(f"Cannot reject a {booking.status} booking.")
    was_confirmed = booking.status == Booking.CONFIRMED
    booking.status = Booking.REJECTED
    booking.email_sent_at = None
    if note:
        booking.admin_note = note
    elif was_confirmed:
        booking.admin_note = CANCELLED_NOTE
    return save_booking(booking)


def block_slot(booking_date, slot_time, reason: str) -> Booking:
    """Create a BLOCKED row so customers cannot book this slot.

    Raises SlotUnavailableError if the slot is already taken.
    """
    return save_booking(Booking(
        booking_code=generate_booking_code(),
        customer_name=None,
        phone=None,
        booking_date=booking_date,
        slot_time=slot_time,
        status=Booking.BLOCKED,
        admin_note=(reason or "").strip() or None,
    ))


def unblock_slot(booking_id: int) -> None:
    """Delete a BLOCKED row. Raises InvalidTransitionError if it is not a block."""
    booking = _get(booking_id)
    if booking.status != Booking.BLOCKED:
        raise InvalidTransitionError("That booking is not a block.")
    db.session.delete(booking)
    db.session.commit()


def bookings_for_day(day: date) -> list[Booking]:
    """Every active row of operating day `day` (06:00 on `day` to 06:00 the next day),
    in time order (admin view - includes customer data)."""
    rows = db.session.scalars(
        db.select(Booking).where(
            Booking.status.in_(Booking.ACTIVE_STATUSES),
            db.or_(
                db.and_(Booking.booking_date == day, Booking.slot_time >= DAY_START),
                db.and_(Booking.booking_date == day + timedelta(days=1), Booking.slot_time < DAY_START),
            ),
        )
    )
    return sorted(rows, key=lambda b: (b.booking_date, b.slot_time))


def dashboard_summary(today: date) -> dict:
    """Numbers and lists for the admin dashboard. `today` is the current operating day (CR-10)."""
    week_end = today + timedelta(days=6)
    week = list(db.session.scalars(
        db.select(Booking)
        .where(
            Booking.booking_date >= today,
            Booking.booking_date <= week_end,
            Booking.status.in_(Booking.ACTIVE_STATUSES),
        )
        .order_by(Booking.booking_date, Booking.slot_time)
    ))
    pending_count = db.session.scalar(
        db.select(db.func.count())
        .select_from(Booking)
        .where(Booking.status == Booking.PENDING, Booking.booking_date >= today)
    )
    to_check = [b for b in week if b.status == Booking.PENDING]
    to_check += db.session.scalars(  # PENDING further ahead than this week
        db.select(Booking)
        .where(Booking.status == Booking.PENDING, Booking.booking_date > week_end)
        .order_by(Booking.booking_date, Booking.slot_time)
    ).all()
    return {
        "today": today,
        "to_check": to_check,
        "todays_bookings": bookings_for_day(today),
        "week": week,
        "pending_count": pending_count or 0,
        "confirmed_this_week": sum(1 for b in week if b.status == Booking.CONFIRMED),
    }
