from flask import Blueprint, render_template

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/login")
def login():
    """Placeholder until M5 builds the real login."""
    return render_template("admin/login.html")
