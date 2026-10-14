from extensions import MYSQL_TABLE_OPTIONS, db
from models._time import utcnow

from database.seed_data import DEFAULT_SETTINGS


class TurfSettings(db.Model):
    """Owner-editable business info. Always a single row with id = 1 (plan D-13)."""

    __tablename__ = "turf_settings"
    __table_args__ = MYSQL_TABLE_OPTIONS

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
    pricing = db.Column(db.JSON, nullable=False, default=list)       # price bands, services/pricing.py
    default_price_bdt = db.Column(db.Integer)                         # for slots no band covers (D-47)
    slot_times = db.Column(db.JSON)                                   # 12 "HH:MM" starts; NULL = SLOT_TIMES (CR-6)
    facilities = db.Column(db.JSON, nullable=False, default=list)  # unused since CR-5; kept so it can return without a migration
    reviews = db.Column(db.JSON, nullable=False, default=list)
    gallery = db.Column(db.JSON, nullable=False, default=list)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    @classmethod
    def current(cls) -> "TurfSettings | None":
        return db.session.get(cls, 1)

    @classmethod
    def current_or_default(cls) -> "TurfSettings":
        """The saved row, or a transient row of `TODO(owner)` placeholders.

        Lets public pages render before `flask seed-settings` has been run.
        The returned object is NOT added to the session when it is a default.
        """
        return cls.current() or cls(**DEFAULT_SETTINGS)
