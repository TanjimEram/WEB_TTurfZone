"""Slot prices (M4.7): band resolution, fallback, homepage rundown, API prices."""
from datetime import date, time, timedelta

from extensions import db
from models import Booking, TurfSettings
from services.bookings import generate_booking_code, save_booking
from services.pricing import day_kind, price_table, resolve, rundown
from services.slots import today_dhaka

ALL = ["06:00", "07:30", "09:00", "10:30", "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30"]
DAY = ALL[:7]      # 06:00 .. 15:00
EVENING = ALL[7:]  # 16:30 .. 22:30


def band(label, slots, price, days="all"):
    return {"label": label, "slots": slots, "days": days, "price_bdt": price}


def owner_prices():
    """The owner's example: daytime 4000, after sundown 4500, weekend evenings 5000."""
    return TurfSettings(turf_name="T", default_price_bdt=None, pricing=[
        band("Daytime", DAY, 4000),
        band("Evening", EVENING, 4500),
        band("Weekend evening", EVENING, 5000, days="weekend"),
    ])


def test_weekend_is_friday_and_saturday():
    assert day_kind(date(2026, 10, 16)) == "weekend"   # Friday
    assert day_kind(date(2026, 10, 17)) == "weekend"   # Saturday
    assert day_kind(date(2026, 10, 18)) == "weekday"   # Sunday
    assert day_kind(date(2026, 10, 15)) == "weekday"   # Thursday


def test_specific_day_band_beats_all_days_band_regardless_of_order():
    bands = owner_prices().pricing
    assert resolve(bands, None, "18:00", "weekend") == {"price_bdt": 5000, "band": "Weekend evening"}
    assert resolve(bands, None, "18:00", "weekday") == {"price_bdt": 4500, "band": "Evening"}
    assert resolve(bands, None, "06:00", "weekend") == {"price_bdt": 4000, "band": "Daytime"}


def test_among_equal_bands_the_higher_one_in_the_list_wins():
    bands = [band("First", ["06:00"], 1000), band("Second", ["06:00"], 2000)]
    assert resolve(bands, None, "06:00", "weekday")["band"] == "First"


def test_unmatched_slot_falls_back_to_default_then_none():
    bands = [band("Daytime", DAY, 4000)]
    assert resolve(bands, 3500, "18:00", "weekday") == {"price_bdt": 3500, "band": None}
    assert resolve(bands, None, "18:00", "weekday") == {"price_bdt": None, "band": None}


def test_every_slot_resolves_to_exactly_one_price_on_both_day_types():
    table = price_table(owner_prices())
    for kind, rows in table.items():
        assert [r["time"] for r in rows] == ALL, kind
        assert all(isinstance(r["price_bdt"], int) for r in rows), kind
    assert [r["price_bdt"] for r in table["weekday"]] == [4000] * 7 + [4500] * 5
    assert [r["price_bdt"] for r in table["weekend"]] == [4000] * 7 + [5000] * 5


def test_rundown_merges_bands_and_splits_weekend_when_prices_differ():
    blocks = rundown(owner_prices())
    assert [b["days"] for b in blocks] == ["Sunday to Thursday", "Friday and Saturday"]
    weekday, weekend = blocks
    assert weekday["rows"] == [
        {"start": "06:00 AM", "end": "04:30 PM", "price_bdt": 4000, "band": "Daytime"},
        {"start": "04:30 PM", "end": "12:00 AM", "price_bdt": 4500, "band": "Evening"},
    ]
    assert weekend["rows"][1] == {"start": "04:30 PM", "end": "12:00 AM", "price_bdt": 5000, "band": "Weekend evening"}


def test_rundown_is_one_block_when_every_day_costs_the_same():
    blocks = rundown(TurfSettings(turf_name="T", pricing=[band("Flat", ALL, 3000)]))
    assert blocks == [{"days": "Every day", "rows": [
        {"start": "06:00 AM", "end": "12:00 AM", "price_bdt": 3000, "band": "Flat"}]}]


def test_rundown_shows_default_price_slots_without_a_band_name():
    blocks = rundown(TurfSettings(turf_name="T", default_price_bdt=3500, pricing=[band("Daytime", DAY, 4000)]))
    assert blocks[0]["rows"][1] == {"start": "04:30 PM", "end": "12:00 AM", "price_bdt": 3500, "band": None}


def test_rundown_is_empty_before_any_price_is_set():
    assert rundown(TurfSettings(turf_name="T", pricing=[])) == []


# --- API --------------------------------------------------------------------

def _next(weekday: int) -> date:
    """The next date (from 2 days out, inside the window) with this weekday()."""
    d = today_dhaka() + timedelta(days=2)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d


def test_availability_api_carries_resolved_prices_and_no_customer_data(app, client):
    db.session.add(owner_prices())
    db.session.commit()
    friday, sunday = _next(4), _next(6)
    save_booking(Booking(booking_code=generate_booking_code(), customer_name="Secret Name",
                         phone="01799999999", booking_date=friday, slot_time=time(18, 0),
                         status=Booking.CONFIRMED))

    fri = client.get(f"/api/availability?date={friday.isoformat()}")
    sun = client.get(f"/api/availability?date={sunday.isoformat()}").get_json()
    prices_fri = {s["time"]: s["price_bdt"] for s in fri.get_json()["slots"]}
    prices_sun = {s["time"]: s["price_bdt"] for s in sun["slots"]}
    assert prices_fri["06:00"] == 4000 and prices_fri["18:00"] == 5000
    assert prices_sun["06:00"] == 4000 and prices_sun["18:00"] == 4500

    text = fri.get_data(as_text=True)
    assert "Secret Name" not in text and "01799999999" not in text
    assert all(set(s) == {"time", "label", "state", "price_bdt"} for s in fri.get_json()["slots"])


def test_availability_api_price_is_null_before_prices_are_set(client):
    body = client.get(f"/api/availability?date={_next(6).isoformat()}").get_json()
    assert {s["price_bdt"] for s in body["slots"]} == {None}
