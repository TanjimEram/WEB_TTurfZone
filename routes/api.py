from datetime import date

from flask import Blueprint, jsonify, request

from services.slots import get_day_availability

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/availability")
def availability():
    """GET /api/availability?date=YYYY-MM-DD -> slot states for that day.

    Public: never includes customer names or phone numbers (only slot states).
    Not cached: slot states change the moment a booking is made.
    """
    raw = request.args.get("date", "")
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        return jsonify(error="Use ?date=YYYY-MM-DD"), 400
    response = jsonify(date=day.isoformat(), slots=get_day_availability(day))
    response.headers["Cache-Control"] = "no-store"
    return response
