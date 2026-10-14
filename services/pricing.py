"""Slot prices (M4.7).

turf_settings.pricing is a list of bands, in the owner's order:

    {"label": "Daytime", "slots": ["06:00", "07:30", ...], "days": "all", "price_bdt": 4000}

`days` is "all", "weekday" or "weekend". turf_settings.default_price_bdt covers
any slot no band matches.

Resolution rule (D-47), the same everywhere (slot grid, homepage, admin preview):
  1. a band for this day type ("weekday"/"weekend") that lists the slot;
  2. otherwise a band for "all" days that lists the slot;
  3. otherwise the default price (shown as the fallback in the admin);
  4. no default either: None, which the site shows as "price on request".
Within steps 1 and 2 the band higher in the list wins. So every slot resolves to
exactly one price (or None before the owner has set any).
"""
from datetime import date, datetime, timedelta

from services.slots import SLOT_MINUTES, slot_label, slot_times

# D-46: Bangladesh's official weekend. Assumption until the owner confirms (C-31).
WEEKEND_DAYS = (4, 5)  # date.weekday(): Friday, Saturday
DAY_KINDS = {"weekday": "Sunday to Thursday", "weekend": "Friday and Saturday"}  # change with WEEKEND_DAYS


def day_kind(d: date) -> str:
    """'weekend' or 'weekday' for a date."""
    return "weekend" if d.weekday() in WEEKEND_DAYS else "weekday"


def resolve(bands: list, default_price: int | None, slot_key: str, kind: str) -> dict:
    """The price for one slot on one day type: {"price_bdt": int | None, "band": label | None}.

    `band` is None when the default price (or nothing) applied. See the module docstring.
    """
    for wanted in (kind, "all"):
        for band in bands or []:
            if band.get("days", "all") == wanted and slot_key in band.get("slots", []):
                return {"price_bdt": band["price_bdt"], "band": band["label"]}
    return {"price_bdt": default_price, "band": None}


def price_table(settings, times=None) -> dict:
    """Every slot's price for both day types: {"weekday": [row, ...], "weekend": [...]}.

    row = {"time": "06:00", "label": "06:00 AM", "price_bdt": int | None, "band": str | None}.
    `times` defaults to the current slot times; the admin preview passes unsaved ones.
    """
    times = times or slot_times(settings)
    table = {}
    for kind in DAY_KINDS:
        table[kind] = [
            {"time": t.strftime("%H:%M"), "label": slot_label(t),
             **resolve(settings.pricing, settings.default_price_bdt, t.strftime("%H:%M"), kind)}
            for t in times
        ]
    return table


def prices_for_day(settings, d: date) -> dict:
    """{"06:00": price or None, ...} for one date."""
    return {row["time"]: row["price_bdt"] for row in price_table(settings)[day_kind(d)]}


def rundown(settings) -> list[dict]:
    """The homepage price list, built from the resolved prices (so it can never
    disagree with the slot grid). Consecutive slots with the same price and band
    are merged into one row:

        [{"days": "Every day", "rows": [{"start": "06:00 AM", "end": "04:30 PM",
                                         "price_bdt": 4000, "band": "Daytime"}, ...]}]

    Returns [] when no slot has a price yet (the page then shows a TODO note).
    """
    table = price_table(settings)
    if all(row["price_bdt"] is None for rows in table.values() for row in rows):
        return []
    times = slot_times(settings)
    same = [(r["price_bdt"], r["band"]) for r in table["weekday"]] == \
           [(r["price_bdt"], r["band"]) for r in table["weekend"]]
    kinds = [("Every day", "weekday")] if same else [(DAY_KINDS[k], k) for k in DAY_KINDS]
    return [{"days": title, "rows": _merge_rows(table[kind], times)} for title, kind in kinds]


def _merge_rows(rows: list, times: list) -> list[dict]:
    merged = []
    for row, t in zip(rows, times):
        end = (datetime.combine(date.min, t) + timedelta(minutes=SLOT_MINUTES)).time()
        last = merged[-1] if merged else None
        if last and (last["price_bdt"], last["band"]) == (row["price_bdt"], row["band"]):
            last["end"] = slot_label(end)
        else:
            merged.append({"start": row["label"], "end": slot_label(end),
                           "price_bdt": row["price_bdt"], "band": row["band"]})
    return merged
