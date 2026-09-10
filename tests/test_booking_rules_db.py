"""The database itself must refuse double bookings (plan D-04)."""
from datetime import date, time

import pytest
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Booking
from services.bookings import SlotUnavailableError, generate_booking_code, save_booking

DAY = date(2030, 1, 15)
SIX_PM = time(18, 0)


def make(status=Booking.PENDING, slot=SIX_PM, code=None):
    return Booking(
        booking_code=code or generate_booking_code(),
        customer_name="Test Player",
        phone="01700000001",
        booking_date=DAY,
        slot_time=slot,
        status=status,
    )


def test_booking_code_format(app):
    code = generate_booking_code()
    assert code.startswith("TZ-") and len(code) == 9
    assert not set(code[3:]) & set("01IO")


def test_same_slot_cannot_be_booked_twice(app):
    save_booking(make())
    with pytest.raises(SlotUnavailableError):
        save_booking(make())


def test_confirmed_slot_cannot_be_booked(app):
    save_booking(make(status=Booking.CONFIRMED))
    with pytest.raises(SlotUnavailableError):
        save_booking(make())


def test_blocked_slot_cannot_be_booked(app):
    save_booking(make(status=Booking.BLOCKED))
    with pytest.raises(SlotUnavailableError):
        save_booking(make())


def test_rejected_booking_frees_the_slot(app):
    first = save_booking(make())
    first.status = Booking.REJECTED
    db.session.commit()
    assert save_booking(make()).id is not None


def test_different_slots_on_same_day_are_allowed(app):
    save_booking(make(slot=time(18, 0)))
    assert save_booking(make(slot=time(19, 30))).id is not None


def test_unknown_status_is_rejected_by_database(app):
    db.session.add(make(status="MAYBE"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
