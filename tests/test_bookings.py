"""Booking service rules (M2.3). SQLite in-memory; the DB still enforces uq_active_slot."""
import datetime as dt

import pytest

from extensions import db
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
    normalize_trx_id,
    reject_booking,
    save_booking,
    unblock_slot,
)
from services.slots import today_dhaka

SOON = today_dhaka() + dt.timedelta(days=3)      # inside the window, all slots future
SIX_PM = dt.time(18, 0)


_TRX = iter(f"TRX{n:07d}" for n in range(1, 100_000))


def _req(name, phone, day, slot, **payment):
    """create_booking_request with valid payment details unless a test overrides them."""
    payment.setdefault("email", "player@example.test")
    payment.setdefault("payer_number", "01812345678")
    payment.setdefault("trx_id", next(_TRX))
    return create_booking_request(name, phone, day, slot, **payment)


# --- phone normalisation ------------------------------------------------

@pytest.mark.parametrize("raw", ["01712345678", "+8801712345678", "8801712345678", "017-1234 5678"])
def test_normalize_phone_accepts_known_forms(raw):
    assert normalize_phone(raw) == "01712345678"


@pytest.mark.parametrize("raw", ["", "12345", "0171234567", "01234567890", "0191234567a"])
def test_normalize_phone_rejects_bad(raw):
    with pytest.raises(BookingValidationError):
        normalize_phone(raw)


# --- create_booking_request -------------------------------------------

def test_new_booking_is_pending_with_payment_details(app):
    """CR-9: a booking waits for the owner to check the bKash payment (PENDING holds the slot)."""
    booking = _req("Rafi", "+8801712345678", SOON, SIX_PM, email="a@b.test",
                   payer_number="+8801812345678", trx_id=" 8n7a6d5e4f ")
    assert booking.id is not None
    assert booking.status == Booking.PENDING
    assert (booking.phone, booking.payer_number) == ("01712345678", "01812345678")
    assert (booking.customer_email, booking.trx_id) == ("a@b.test", "8N7A6D5E4F")
    assert booking.booking_code.startswith("TZ-")


def test_pending_booking_holds_the_slot(app):
    _req("Rafi", "01712345678", SOON, SIX_PM)
    with pytest.raises(SlotUnavailableError):
        _req("Other", "01812345678", SOON, SIX_PM)


@pytest.mark.parametrize("raw", ["12", "abc def ghi", "8N7A6D5E4F1234", "8N7A-6D5E"])
def test_normalize_trx_id_rejects_bad(raw):
    with pytest.raises(BookingValidationError):
        normalize_trx_id(raw)


def test_bad_trx_id_and_payer_number_are_reported_together(app):
    with pytest.raises(BookingValidationError) as exc:
        _req("Rafi", "01712345678", SOON, SIX_PM, payer_number="abc", trx_id="12")
    assert set(exc.value.errors) >= {"payer_number", "trx_id"}
    assert db.session.scalar(db.select(db.func.count()).select_from(Booking)) == 0


def test_duplicate_trx_id_is_refused(app):
    _req("Rafi", "01712345678", SOON, SIX_PM, trx_id="8N7A6D5E4F")
    with pytest.raises(BookingValidationError) as exc:
        _req("Sami", "01812345678", SOON, dt.time(19, 0), trx_id="8n7a6d5e4f")
    assert "already been used" in exc.value.errors["trx_id"]


def test_duplicate_trx_id_race_is_a_validation_error(app, monkeypatch):
    _req("Rafi", "01712345678", SOON, SIX_PM, trx_id="8N7A6D5E4F")
    monkeypatch.setattr("services.bookings._trx_id_taken", lambda trx: False)  # the other request's pre-check saw nothing
    with pytest.raises(BookingValidationError) as exc:
        _req("Sami", "01812345678", SOON, dt.time(19, 0), trx_id="8N7A6D5E4F")
    assert "already been used" in exc.value.errors["trx_id"]


def test_blank_name_is_rejected(app):
    with pytest.raises(BookingValidationError) as exc:
        _req("  ", "01712345678", SOON, SIX_PM)
    assert "name" in exc.value.errors


def test_bad_phone_is_rejected(app):
    with pytest.raises(BookingValidationError) as exc:
        _req("Rafi", "123", SOON, SIX_PM)
    assert "phone" in exc.value.errors


def test_name_and_phone_errors_reported_together(app):
    with pytest.raises(BookingValidationError) as exc:
        _req("", "123", SOON, SIX_PM)
    assert set(exc.value.errors) >= {"name", "phone"}


def test_past_slot_is_rejected(app):
    yesterday = today_dhaka() - dt.timedelta(days=1)
    with pytest.raises(BookingValidationError) as exc:
        _req("Rafi", "01712345678", yesterday, SIX_PM)
    assert "slot" in exc.value.errors


def test_same_slot_twice_raises_slot_unavailable(app):
    _req("Rafi", "01712345678", SOON, SIX_PM)
    with pytest.raises(SlotUnavailableError):
        _req("Other", "01812345678", SOON, SIX_PM)


def test_payments_enabled_not_implemented_yet(app):
    """PAYMENTS_ENABLED=true needs the bKash flow (M2.6/M10) - refuses instead of mislabeling."""
    app.config["PAYMENTS_ENABLED"] = True
    try:
        with pytest.raises(NotImplementedError):
            _req("Rafi", "01712345678", SOON, SIX_PM)
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
    first = _req("Rafi", "01712345678", SOON, SIX_PM)
    reject_booking(first.id, note="No show")
    assert first.status == Booking.REJECTED
    again = _req("Sami", "01812345678", SOON, SIX_PM)
    assert again.id is not None


def test_reject_works_on_confirmed(app):
    booking = _req("Rafi", "01712345678", SOON, SIX_PM)
    confirm_booking(booking.id)  # the owner checked the payment
    assert booking.status == Booking.CONFIRMED
    reject_booking(booking.id)
    assert booking.status == Booking.REJECTED


def test_cannot_reject_already_rejected(app):
    booking = _req("Rafi", "01712345678", SOON, SIX_PM)
    reject_booking(booking.id)
    with pytest.raises(InvalidTransitionError):
        reject_booking(booking.id)


# --- block / unblock -----------------------------------------------

def test_block_prevents_booking(app):
    block_slot(SOON, SIX_PM, "Maintenance")
    with pytest.raises(SlotUnavailableError):
        _req("Rafi", "01712345678", SOON, SIX_PM)


def test_block_on_taken_slot_raises(app):
    _req("Rafi", "01712345678", SOON, SIX_PM)
    with pytest.raises(SlotUnavailableError):
        block_slot(SOON, SIX_PM, "too late")


def test_unblock_frees_the_slot(app):
    blocked = block_slot(SOON, SIX_PM, "Maintenance")
    unblock_slot(blocked.id)
    assert _req("Rafi", "01712345678", SOON, SIX_PM).id is not None


def test_unblock_rejects_non_block(app):
    booking = _req("Rafi", "01712345678", SOON, SIX_PM)
    with pytest.raises(InvalidTransitionError):
        unblock_slot(booking.id)
