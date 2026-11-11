"""GET /api/availability?date=D: the 24 slots of operating day D (CR-10). Never customer data."""
from datetime import time, timedelta

from extensions import db
from models import Booking, TurfSettings
from services.bookings import generate_booking_code, save_booking
from services.slots import current_operating_day, slot_label

# An operating day a few days out: inside the 14-day window, and every slot is still future.
DAY_DATE = current_operating_day() + timedelta(days=5)
NEXT_DATE = DAY_DATE + timedelta(days=1)
DAY = DAY_DATE.isoformat()


def add(slot, status, on=DAY_DATE):
    save_booking(Booking(booking_code=generate_booking_code(), customer_name="Secret Name",
                         phone="01799999999", booking_date=on, slot_time=slot, status=status))


def slots(client, day=DAY):
    return client.get(f"/api/availability?date={day}").get_json()["slots"]


def test_slot_label_uses_12_hour_clock():
    assert slot_label(time(13, 0)) == "01:00 PM"


def test_availability_returns_24_hourly_slots_in_operating_order(client):
    body = client.get(f"/api/availability?date={DAY}").get_json()
    assert body["date"] == DAY
    times = [s["time"] for s in body["slots"]]
    assert len(times) == 24 and times[0] == "06:00" and times[17] == "23:00" and times[-1] == "05:00"
    assert {s["state"] for s in body["slots"]} == {"available"}


def test_after_midnight_slots_carry_the_next_calendar_date(client):
    by_time = {s["time"]: s for s in slots(client)}
    assert by_time["23:00"]["date"] == DAY and by_time["23:00"]["period"] == "night"
    assert by_time["01:00"]["date"] == NEXT_DATE.isoformat() and by_time["01:00"]["period"] == "night"
    assert by_time["07:00"]["period"] == "morning" and by_time["14:00"]["period"] == "afternoon"


def test_availability_shows_each_state(app, client):
    add(time(6), Booking.PENDING)
    add(time(7), Booking.CONFIRMED)
    add(time(9), Booking.BLOCKED)
    add(time(10), Booking.REJECTED)
    add(time(1), Booking.CONFIRMED, on=NEXT_DATE)  # this night, after midnight
    add(time(1), Booking.CONFIRMED, on=DAY_DATE)   # the previous night: not this operating day
    states = {s["time"]: s["state"] for s in slots(client)}
    assert states["06:00"] == "pending"
    assert states["07:00"] == "booked"
    assert states["09:00"] == "blocked"
    assert states["10:00"] == "available"
    assert states["01:00"] == "booked"


def test_prices_follow_the_period(app, client):
    db.session.add(TurfSettings(id=1, turf_name="T", pricing={"morning": 1000, "afternoon": 1350, "night": 2000}))
    db.session.commit()
    prices = {s["time"]: s["price_bdt"] for s in slots(client)}
    assert prices["06:00"] == 1000 and prices["15:00"] == 1350 and prices["01:00"] == 2000


def test_price_is_null_before_prices_are_set(client):
    assert {s["price_bdt"] for s in slots(client)} == {None}


def test_availability_never_exposes_customer_data(app, client):
    add(time(6), Booking.CONFIRMED)
    text = client.get(f"/api/availability?date={DAY}").get_data(as_text=True)
    assert "Secret Name" not in text and "01799999999" not in text


def test_slot_shape(client):
    assert set(slots(client)[0]) == {"time", "label", "date", "period", "state", "price_bdt"}


def test_bad_date_returns_400(client):
    response = client.get("/api/availability?date=not-a-date")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_missing_date_returns_400(client):
    response = client.get("/api/availability")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_date_before_today_returns_400(client):
    yesterday = (current_operating_day() - timedelta(days=1)).isoformat()
    assert client.get(f"/api/availability?date={yesterday}").status_code == 400


def test_date_past_window_returns_400(client):
    far = (current_operating_day() + timedelta(days=90)).isoformat()
    response = client.get(f"/api/availability?date={far}")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_response_is_not_cached(client):
    response = client.get(f"/api/availability?date={DAY}")
    assert response.headers.get("Cache-Control") == "no-store"
