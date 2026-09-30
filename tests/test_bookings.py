"""Booking service rules (M2.3). SQLite in-memory; the DB still enforces uq_active_slot."""
import datetime as dt

import pytest

from models import Booking
from services.bookings import (
    BookingValidationError,
    InvalidTransitionError,
    SlotUnavailableError,
    block_slot,
    confirm_booking,
    create_booking_request,
    generate_booking_code,
    normalize_phone,
    reject_booking,
    save_booking,
    unblock_slot,
)
from services.slots import today_dhaka

SOON = today_dhaka() + dt.timedelta(days=3)      # inside the window, all slots future
SIX_PM = dt.time(18, 0)


# --- phone normalisation ------------------------------------------------

@pytest.mark.parametrize("raw", ["01712345678", "+8801712345678", "8801712345678", "017-1234 5678"])
def test_normalize_phone_accepts_known_forms(raw):
    assert normalize_phone(raw) == "01712345678"


@pytest.mark.parametrize("raw", ["", "12345", "0171234567", "01234567890", "0191234567a"])
def test_normalize_phone_rejects_bad(raw):
    with pytest.raises(BookingValidationError):
        normalize_phone(raw)


# --- create_booking_request -------------------------------------------

def test_valid_request_is_confirmed(app):
    """No manual owner confirmation (CR-2/M4.6): booked means CONFIRMED immediately."""
    booking = create_booking_request("Rafi", "+8801712345678", SOON, SIX_PM)
    assert booking.id is not None
    assert booking.status == Booking.CONFIRMED
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


def test_payments_enabled_not_implemented_yet(app):
    """PAYMENTS_ENABLED=true needs the bKash flow (M2.6/M10) - refuses instead of mislabeling."""
    app.config["PAYMENTS_ENABLED"] = True
    try:
        with pytest.raises(NotImplementedError):
            create_booking_request("Rafi", "01712345678", SOON, SIX_PM)
    finally:
        app.config["PAYMENTS_ENABLED"] = False


# --- confirm / reject ------------------------------------------------
# create_booking_request no longer produces PENDING rows (CR-2/M4.6). The
# manual PENDING->CONFIRMED transition stays available for other paths
# (e.g. a future admin manual booking, M5.6), tested here directly.

def _pending(slot=SIX_PM):
    return save_booking(Booking(
        booking_code=generate_booking_code(), customer_name="Rafi", phone="01712345678",
        booking_date=SOON, slot_time=slot, status=Booking.PENDING,
    ))


def test_confirm_only_from_pending(app):
    booking = _pending()
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
    assert booking.status == Booking.CONFIRMED
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
