from flask import Blueprint, render_template

from models import TurfSettings
from services.slots import SLOT_TIMES, slot_label, today_dhaka

bp = Blueprint("public", __name__)


@bp.context_processor
def inject_common():
    """Values every public template needs.

    now_year: footer copyright.
    wa_link:  wa.me deep link, or "" when the owner has not given a number (C-06).
    """
    settings = TurfSettings.current_or_default()
    digits = (settings.whatsapp or "").strip()
    return {
        "now_year": today_dhaka().year,
        "wa_link": f"https://wa.me/{digits}" if digits else "",
    }


@bp.get("/")
def home():
    """Homepage. All business content comes from turf_settings (plan D-13)."""
    return render_template(
        "index.html",
        settings=TurfSettings.current_or_default(),
        slot_labels=[slot_label(t) for t in SLOT_TIMES],
    )


@bp.get("/healthz")
def healthz():
    """Uptime check. Must not touch the database (plan D-12)."""
    return "ok", 200, {"Content-Type": "text/plain; charset=utf-8"}
