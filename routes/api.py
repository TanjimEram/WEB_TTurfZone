from datetime import date

from flask import Blueprint, jsonify, request

from services.slots import get_day_availability

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/availability")
def availability():
    """GET /api/availability?date=YYYY-MM-DD -> slot states for that day."""
    raw = request.args.get("date", "")
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        return jsonify(error="Use ?date=YYYY-MM-DD"), 400
    return jsonify(date=day.isoformat(), slots=get_day_availability(day))
