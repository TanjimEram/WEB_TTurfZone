from datetime import date, time

from extensions import db
from models import Booking
from services.bookings import generate_booking_code, save_booking
from services.fake_data import FAKE_PREFIX, clear_fake_data, make_fake_bookings, try_double_booking


def test_make_fake_bookings_creates_requested_count(app):
    created = make_fake_bookings(count=8, seed=1)
    assert len(created) == 8
    assert Booking.query.count() == 8
    assert all(b.booking_code.startswith(FAKE_PREFIX) for b in created)


def test_fake_bookings_never_double_book(app):
    make_fake_bookings(count=40, days=4, seed=2)
    active = Booking.query.filter(Booking.status.in_(Booking.ACTIVE_STATUSES)).all()
    keys = [(b.booking_date, b.slot_time) for b in active]
    assert len(keys) == len(set(keys))


def test_try_double_booking_reports_that_database_caught_it(app):
    result = try_double_booking()
    assert result["conflict_caught"] is True


def test_try_double_booking_cleans_up_after_itself(app):
    try_double_booking()
    assert Booking.query.count() == 0


def test_clear_fake_data_keeps_real_bookings(app):
    real = Booking(booking_code=generate_booking_code(), customer_name="Real", phone="01711111111",
                   booking_date=date(2030, 2, 1), slot_time=time(6, 0), status=Booking.CONFIRMED)
    save_booking(real)
    make_fake_bookings(count=5, seed=3)
    assert clear_fake_data() == 5
    assert Booking.query.one().booking_code == real.booking_code
