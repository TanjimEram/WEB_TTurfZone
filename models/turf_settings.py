from extensions import db
from models._time import utcnow


class TurfSettings(db.Model):
    """Owner-editable business info. Always a single row with id = 1 (plan D-13)."""

    __tablename__ = "turf_settings"

    id = db.Column(db.Integer, primary_key=True)
    turf_name = db.Column(db.String(80), nullable=False)
    tagline = db.Column(db.String(160))
    about_text = db.Column(db.Text)
    phone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(20))        # digits with country code, e.g. 8801XXXXXXXXX
    address = db.Column(db.Text)
    map_embed_url = db.Column(db.Text)
    map_link = db.Column(db.Text)
    facebook_url = db.Column(db.Text)
    opening_hours_text = db.Column(db.String(160))
    booking_rules_text = db.Column(db.Text)
    confirm_time_text = db.Column(db.String(160))
    booking_window_days = db.Column(db.Integer, nullable=False, default=14)
    max_pending_per_phone = db.Column(db.Integer, nullable=False, default=2)
    pricing = db.Column(db.JSON, nullable=False, default=list)
    facilities = db.Column(db.JSON, nullable=False, default=list)
    reviews = db.Column(db.JSON, nullable=False, default=list)
    gallery = db.Column(db.JSON, nullable=False, default=list)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    @classmethod
    def current(cls) -> "TurfSettings | None":
        return db.session.get(cls, 1)
