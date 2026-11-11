"""Slot prices (CR-10, D-53): one price per period, the same every day."""
from datetime import time

import pytest

from extensions import db
from models import TurfSettings
from services.pricing import period_prices, price_cards, price_for, prices_for_day
from services.slots import today_dhaka

PRICES = {"morning": 1000, "afternoon": 1350, "night": 2000}


@pytest.fixture
def settings(app):
    row = TurfSettings(id=1, turf_name="T", pricing=dict(PRICES))
    db.session.add(row)
    db.session.commit()
    return row


def test_slot_price_is_its_period_price(settings):
    assert price_for(settings, time(6)) == 1000 and price_for(settings, time(11)) == 1000
    assert price_for(settings, time(12)) == 1350 and price_for(settings, time(17)) == 1350
    assert price_for(settings, time(18)) == 2000


def test_after_midnight_hours_use_night_price(settings):
    assert price_for(settings, time(0)) == 2000 and price_for(settings, time(5)) == 2000


def test_unset_period_price_is_none(settings):
    settings.pricing = {"night": 2000}
    assert price_for(settings, time(9)) is None and price_for(settings, time(20)) == 2000


def test_old_band_list_counts_as_unset(settings):
    settings.pricing = [{"label": "x", "slots": ["06:00"], "days": "all", "price_bdt": 5}]
    assert period_prices(settings) == {"morning": None, "afternoon": None, "night": None}


def test_prices_for_day_covers_the_open_hours(settings):
    prices = prices_for_day(settings, today_dhaka())
    assert len(prices) == 24
    assert prices["06:00"] == 1000 and prices["13:00"] == 1350 and prices["02:00"] == 2000


def test_price_cards_one_per_period(settings):
    cards = price_cards(settings)
    assert [(c["key"], c["name"], c["span"], c["price_bdt"]) for c in cards] == [
        ("morning", "Morning", "6AM–12PM", 1000),
        ("afternoon", "Afternoon", "12PM–6PM", 1350),
        ("night", "Night", "6PM–6AM", 2000),
    ]


def test_price_cards_skip_closed_periods(settings):
    settings.slot_times = ["18:00", "19:00", "02:00"]
    assert [c["key"] for c in price_cards(settings)] == ["night"]


def test_price_cards_empty_without_prices(settings):
    settings.pricing = {}
    assert price_cards(settings) == []
