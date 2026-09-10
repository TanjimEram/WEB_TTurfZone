"""Fake bookings for testing the wiring (development only).

Every fake row has a booking code starting with FK- so it can be removed safely
without touching real bookings.
"""
import random
from datetime import timedelta

from models import Booking
from extensions import db
from services.bookings import SlotUnavailableError, generate_booking_code, save_booking
from services.slots import SLOT_TIMES, today_dhaka

FAKE_PREFIX = "FK-"
FAKE_NAMES = ["Test Rahim", "Test Karim", "Test Nabil", "Test Sakib", "Test Tanvir", "Test Arif"]
_STATUS_WEIGHTS = [(Booking.PENDING, 4), (Booking.CONFIRMED, 4), (Booking.BLOCKED, 1), (Booking.REJECTED, 1)]


def make_fake_bookings(count: int = 10, days: int = 7, seed: int | None = None) -> list[Booking]:
    """Create `count` fake bookings spread over the next `days` days, never double-booking."""
    rng = random.Random(seed)
    start = today_dhaka() + timedelta(days=1)

    taken = {
        (b.booking_date, b.slot_time)
        for b in Booking.query.filter(Booking.status.in_(Booking.ACTIVE_STATUSES)).all()
    }
    positions = [(start + timedelta(days=d), t) for d in range(days) for t in SLOT_TIMES]
    rng.shuffle(positions)
    free = [p for p in positions if p not in taken]

    statuses, weights = zip(*_STATUS_WEIGHTS)
    created = []
    for booking_date, slot_time in free[:count]:
        status = rng.choices(statuses, weights)[0]
        booking = Booking(
            booking_code=generate_booking_code(prefix="FK"),
            customer_name=None if status == Booking.BLOCKED else rng.choice(FAKE_NAMES),
            phone=None if status == Booking.BLOCKED else f"0170000{rng.randint(0, 9999):04d}",
            booking_date=booking_date,
            slot_time=slot_time,
            status=status,
            admin_note="Fake maintenance block" if status == Booking.BLOCKED else None,
        )
        created.append(save_booking(booking))
    return created


def try_double_booking() -> dict:
    """Book one far-future slot twice and report whether the database stopped the second one."""
    booking_date = today_dhaka() + timedelta(days=60)
    slot_time = SLOT_TIMES[8]  # 06:00 PM

    first = Booking(booking_code=generate_booking_code(prefix="FK"), customer_name="Test First",
                    phone="01700000001", booking_date=booking_date, slot_time=slot_time, status=Booking.PENDING)
    second = Booking(booking_code=generate_booking_code(prefix="FK"), customer_name="Test Second",
                     phone="01700000002", booking_date=booking_date, slot_time=slot_time, status=Booking.PENDING)

    created_first = False
    try:
        save_booking(first)
        created_first = True
    except SlotUnavailableError:
        pass  # slot already held by some other row; the second attempt below still tests the rule

    try:
        save_booking(second)
        caught = False
        db.session.delete(second)
        db.session.commit()
    except SlotUnavailableError:
        caught = True

    if created_first:
        db.session.delete(first)
        db.session.commit()

    return {
        "conflict_caught": caught,
        "message": "Database caught the double booking." if caught
        else "WARNING: second booking was accepted. The uq_active_slot index is missing.",
    }


def clear_fake_data() -> int:
    """Delete all FK- bookings. Returns how many rows were removed."""
    deleted = Booking.query.filter(Booking.booking_code.startswith(FAKE_PREFIX)).delete(synchronize_session=False)
    db.session.commit()
    return deleted
