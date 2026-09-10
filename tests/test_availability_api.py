from datetime import time, timedelta

from models import Booking
from services.bookings import generate_booking_code, save_booking
from services.slots import SLOT_TIMES, slot_label, today_dhaka

# A date a few days out: inside the 14-day window, and every slot is still future.
DAY_DATE = today_dhaka() + timedelta(days=5)
DAY = DAY_DATE.isoformat()


def add(slot, status):
    save_booking(Booking(booking_code=generate_booking_code(), customer_name="Secret Name",
                         phone="01799999999", booking_date=DAY_DATE, slot_time=slot, status=status))


def test_there_are_twelve_ninety_minute_slots():
    assert len(SLOT_TIMES) == 12
    assert SLOT_TIMES[0] == time(6, 0) and SLOT_TIMES[-1] == time(22, 30)


def test_slot_label_uses_12_hour_clock():
    assert slot_label(time(13, 30)) == "01:30 PM"


def test_availability_returns_all_slots(client):
    body = client.get(f"/api/availability?date={DAY}").get_json()
    assert body["date"] == DAY
    assert len(body["slots"]) == 12
    assert {s["state"] for s in body["slots"]} == {"available"}


def test_availability_shows_each_state(app, client):
    add(time(6, 0), Booking.PENDING)
    add(time(7, 30), Booking.CONFIRMED)
    add(time(9, 0), Booking.BLOCKED)
    add(time(10, 30), Booking.REJECTED)
    states = {s["time"]: s["state"] for s in client.get(f"/api/availability?date={DAY}").get_json()["slots"]}
    assert states["06:00"] == "pending"
    assert states["07:30"] == "booked"
    assert states["09:00"] == "blocked"
    assert states["10:30"] == "available"


def test_availability_never_exposes_customer_data(app, client):
    add(time(6, 0), Booking.CONFIRMED)
    text = client.get(f"/api/availability?date={DAY}").get_data(as_text=True)
    assert "Secret Name" not in text and "01799999999" not in text


def test_bad_date_returns_400(client):
    response = client.get("/api/availability?date=not-a-date")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_missing_date_returns_400(client):
    response = client.get("/api/availability")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_date_before_today_returns_400(client):
    yesterday = (today_dhaka() - timedelta(days=1)).isoformat()
    assert client.get(f"/api/availability?date={yesterday}").status_code == 400


def test_date_past_window_returns_400(client):
    far = (today_dhaka() + timedelta(days=90)).isoformat()
    response = client.get(f"/api/availability?date={far}")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_response_is_not_cached(client):
    response = client.get(f"/api/availability?date={DAY}")
    assert response.headers.get("Cache-Control") == "no-store"


def test_slot_shape_is_state_only(client):
    slot = client.get(f"/api/availability?date={DAY}").get_json()["slots"][0]
    assert set(slot) == {"time", "label", "state", "price_bdt"}
