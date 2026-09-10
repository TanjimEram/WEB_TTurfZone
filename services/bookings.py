"""Booking operations.

This file currently has the database-safe save used by everything else.
M2.3 adds: create_booking_request, confirm_booking, reject_booking, block_slot, unblock_slot.
"""
import secrets

from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Booking

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I, easy to read out on the phone


class SlotUnavailableError(Exception):
    """The slot is already pending, confirmed or blocked."""


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
