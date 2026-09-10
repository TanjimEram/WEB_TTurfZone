"""Booking operations.

`save_booking` is the database-safe insert/update everything commits through.
M2.3 adds the request/owner actions: create_booking_request, confirm_booking,
reject_booking, block_slot, unblock_slot, plus phone normalisation.
"""
import re
import secrets
from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Booking, TurfSettings
from services.slots import is_bookable, today_dhaka

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
    message = str(exc.orig)
    return "uq_active_slot" in message or "bookings.booking_date, bookings.slot_time" in message


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


def _clean_name(raw: str) -> str:
    name = (raw or "").strip()
    if not (1 <= len(name) <= 80):
        raise BookingValidationError({"name": "Enter your name (up to 80 characters)."})
    return name


def _settings() -> TurfSettings:
    return TurfSettings.current_or_default()


# --------------------------------------------------------------- actions

def create_booking_request(name: str, phone: str, booking_date, slot_time) -> Booking:
    """Validate and insert a PENDING booking request.

    Raises BookingValidationError (bad name/phone, slot not bookable, pending cap)
    or SlotUnavailableError (slot taken between the page load and submit).
    """
    errors: dict[str, str] = {}

    try:
        clean_name = _clean_name(name)
    except BookingValidationError as exc:
        errors.update(exc.errors)
        clean_name = ""

    try:
        clean_phone = normalize_phone(phone)
    except BookingValidationError as exc:
        errors.update(exc.errors)
        clean_phone = ""

    if not is_bookable(booking_date, slot_time):
        errors["slot"] = "That slot can no longer be booked."

    if clean_phone and "phone" not in errors:
        cap = _settings().max_pending_per_phone or 2
        pending = db.session.scalar(
            db.select(db.func.count())
            .select_from(Booking)
            .where(
                Booking.phone == clean_phone,
                Booking.status == Booking.PENDING,
                Booking.booking_date >= today_dhaka(),
            )
        )
        if pending >= cap:
            errors["phone"] = f"You already have {cap} pending requests. Please wait for those to be confirmed."

    if errors:
        raise BookingValidationError(errors)

    return save_booking(Booking(
        booking_code=generate_booking_code(),
        customer_name=clean_name,
        phone=clean_phone,
        booking_date=booking_date,
        slot_time=slot_time,
        status=Booking.PENDING,
    ))


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
    return save_booking(booking)


def reject_booking(booking_id: int, note: str | None = None) -> Booking:
    """PENDING or CONFIRMED -> REJECTED (frees the slot). Used for 'reject' and 'cancel'."""
    booking = _get(booking_id)
    if booking.status not in (Booking.PENDING, Booking.CONFIRMED):
        raise InvalidTransitionError(f"Cannot reject a {booking.status} booking.")
    booking.status = Booking.REJECTED
    if note:
        booking.admin_note = note
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
    """Every active row for one day (admin view - includes customer data)."""
    return list(db.session.scalars(
        db.select(Booking)
        .where(Booking.booking_date == day, Booking.status.in_(Booking.ACTIVE_STATUSES))
        .order_by(Booking.slot_time)
    ))


def dashboard_summary(today: date) -> dict:
    """Numbers and lists for the admin dashboard."""
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
    return {
        "today": today,
        "todays_bookings": [b for b in week if b.booking_date == today],
        "week": week,
        "pending_count": pending_count or 0,
        "confirmed_this_week": sum(1 for b in week if b.status == Booking.CONFIRMED),
    }
