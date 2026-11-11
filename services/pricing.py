"""Slot prices (CR-10, D-53): one price per period, the same every day.

turf_settings.pricing = {"morning": 1000, "afternoon": 1350, "night": 2000}

The owner sets the three prices once in Settings and they apply to every day
until changed. A slot costs its period's price; the 00:00-05:00 hours belong to
Night. A period with no price yet gives None, which the site shows as "On request".
"""
from datetime import date, time

from services.slots import PERIODS, period_of, slot_times


def period_prices(settings) -> dict:
    """{"morning": int | None, "afternoon": ..., "night": ...} from turf_settings.pricing.

    Anything that isn't the three-price dict (e.g. the old M4.7 band list) counts as unset.
    """
    saved = settings.pricing if isinstance(settings.pricing, dict) else {}
    return {p["key"]: saved.get(p["key"]) for p in PERIODS}


def price_for(settings, t: time) -> int | None:
    """The price of the slot starting at `t`: its period's price."""
    return period_prices(settings)[period_of(t)]


def prices_for_day(settings, day: date) -> dict:
    """{"HH:MM": int | None} for the open hours. `day` doesn't change the price (D-53)."""
    prices = period_prices(settings)
    return {t.strftime("%H:%M"): prices[period_of(t)] for t in slot_times(settings)}


def price_cards(settings) -> list[dict]:
    """Homepage pricing: one card per period that has an open hour.

    [{"key", "name", "span", "price_bdt"}]; [] until any period has a price.
    """
    prices = period_prices(settings)
    if all(price is None for price in prices.values()):
        return []
    open_periods = {period_of(t) for t in slot_times(settings)}
    return [{"key": p["key"], "name": p["name"], "span": p["span"], "price_bdt": prices[p["key"]]}
            for p in PERIODS if p["key"] in open_periods]
