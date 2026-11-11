from datetime import date

from flask import Blueprint, jsonify, request

from models import TurfSettings
from services.pricing import prices_for_day
from services.slots import get_day_availability, is_within_window

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/availability")
def availability():
    """GET /api/availability?date=YYYY-MM-DD -> the slots of that operating day (CR-10).

    Public: never includes customer names or phone numbers - only each slot's
    time, label, real calendar date, period, state and price_bdt (its period's price, D-53).
    Not cached: slot states change the moment a booking is made.
    Dates outside the booking window are rejected (400) - the client is
    never trusted to stay inside it.
    """
    raw = request.args.get("date", "")
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        return jsonify(error="Use ?date=YYYY-MM-DD"), 400
    if not is_within_window(day):
        return jsonify(error="Date is outside the booking window"), 400
    prices = prices_for_day(TurfSettings.current_or_default(), day)
    slots = [{**slot, "price_bdt": prices.get(slot["time"])} for slot in get_day_availability(day)]
    response = jsonify(date=day.isoformat(), slots=slots)
    response.headers["Cache-Control"] = "no-store"
    return response
