"""Booking service rules (M2.3). SQLite in-memory; the DB still enforces uq_active_slot."""
import datetime as dt

import pytest

from models import Booking, TurfSettings
from services.bookings import (
    BookingValidationError,
    InvalidTransitionError,
    SlotUnavailableError,
    block_slot,
    confirm_booking,
    create_booking_request,
    normalize_phone,
    reject_booking,
    unblock_slot,
)
from services.slots import today_dhaka

SOON = today_dhaka() + dt.timedelta(days=3)      # inside the window, all slots future
SIX_PM = dt.time(18, 0)
SEVEN_THIRTY = dt.time(19, 30)
NINE_PM = dt.time(21, 0)


# --- phone normalisation ------------------------------------------------

@pytest.mark.parametrize("raw", ["01712345678", "+8801712345678", "8801712345678", "017-1234 5678"])
def test_normalize_phone_accepts_known_forms(raw):
    assert normalize_phone(raw) == "01712345678"


@pytest.mark.parametrize("raw", ["", "12345", "0171234567", "01234567890", "0191234567a"])
def test_normalize_phone_rejects_bad(raw):
    with pytest.raises(BookingValidationError):
        normalize_phone(raw)


# --- create_booking_request -------------------------------------------

def test_valid_request_is_pending(app):
    booking = create_booking_request("Rafi", "+8801712345678", SOON, SIX_PM)
    assert booking.id is not None
    assert booking.status == Booking.PENDING
    assert booking.phone == "01712345678"
    assert booking.booking_code.startswith("TZ-")


def test_blank_name_is_rejected(app):
    with pytest.raises(BookingValidationError) as exc:
        create_booking_request("  ", "01712345678", SOON, SIX_PM)
    assert "name" in exc.value.errors


def test_bad_phone_is_rejected(app):
    with pytest.raises(BookingValidationError) as exc:
        create_booking_request("Rafi", "123", SOON, SIX_PM)
    assert "phone" in exc.value.errors


def test_name_and_phone_errors_reported_together(app):
    with pytest.raises(BookingValidationError) as exc:
        create_booking_request("", "123", SOON, SIX_PM)
    assert set(exc.value.errors) >= {"name", "phone"}


def test_past_slot_is_rejected(app):
    yesterday = today_dhaka() - dt.timedelta(days=1)
    with pytest.raises(BookingValidationError) as exc:
        create_booking_request("Rafi", "01712345678", yesterday, SIX_PM)
    assert "slot" in exc.value.errors


def test_same_slot_twice_raises_slot_unavailable(app):
    create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    with pytest.raises(SlotUnavailableError):
        create_booking_request("Other", "01812345678", SOON, SIX_PM)


def test_pending_cap_per_phone(app):
    create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    create_booking_request("Rafi", "01712345678", SOON, SEVEN_THIRTY)
    with pytest.raises(BookingValidationError) as exc:
        create_booking_request("Rafi", "01712345678", SOON, NINE_PM)
    assert "phone" in exc.value.errors


def test_pending_cap_is_per_phone_not_global(app):
    create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    create_booking_request("Rafi", "01712345678", SOON, SEVEN_THIRTY)
    # a different phone is unaffected
    assert create_booking_request("Sami", "01812345678", SOON, NINE_PM).id is not None


# --- confirm / reject ------------------------------------------------

def test_confirm_only_from_pending(app):
    booking = create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    confirmed = confirm_booking(booking.id)
    assert confirmed.status == Booking.CONFIRMED
    with pytest.raises(InvalidTransitionError):
        confirm_booking(booking.id)


def test_reject_frees_the_slot(app):
    first = create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    reject_booking(first.id, note="No show")
    assert first.status == Booking.REJECTED
    again = create_booking_request("Sami", "01812345678", SOON, SIX_PM)
    assert again.id is not None


def test_reject_works_on_confirmed(app):
    booking = create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    confirm_booking(booking.id)
    reject_booking(booking.id)
    assert booking.status == Booking.REJECTED


def test_cannot_reject_already_rejected(app):
    booking = create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    reject_booking(booking.id)
    with pytest.raises(InvalidTransitionError):
        reject_booking(booking.id)


# --- block / unblock -----------------------------------------------

def test_block_prevents_booking(app):
    block_slot(SOON, SIX_PM, "Maintenance")
    with pytest.raises(SlotUnavailableError):
        create_booking_request("Rafi", "01712345678", SOON, SIX_PM)


def test_block_on_taken_slot_raises(app):
    create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    with pytest.raises(SlotUnavailableError):
        block_slot(SOON, SIX_PM, "too late")


def test_unblock_frees_the_slot(app):
    blocked = block_slot(SOON, SIX_PM, "Maintenance")
    unblock_slot(blocked.id)
    assert create_booking_request("Rafi", "01712345678", SOON, SIX_PM).id is not None


def test_unblock_rejects_non_block(app):
    booking = create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    with pytest.raises(InvalidTransitionError):
        unblock_slot(booking.id)


def test_max_pending_per_phone_reads_settings(app):
    from extensions import db
    db.session.add(TurfSettings(turf_name="TTURFZONE", max_pending_per_phone=1))
    db.session.commit()
    create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    with pytest.raises(BookingValidationError):
        create_booking_request("Rafi", "01712345678", SOON, SEVEN_THIRTY)
