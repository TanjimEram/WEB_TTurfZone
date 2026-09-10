from flask import Blueprint, render_template

from models import TurfSettings

bp = Blueprint("public", __name__)


@bp.get("/")
def home():
    return render_template("index.html", settings=TurfSettings.current())


@bp.get("/healthz")
def healthz():
    """Uptime check. Must not touch the database (plan D-12)."""
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}
