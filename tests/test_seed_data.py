from sqlalchemy import String

from database.seed_data import DEFAULT_SETTINGS
from models import TurfSettings


def test_seed_values_fit_their_columns():
    """SQLite ignores VARCHAR lengths but PostgreSQL rejects values that are too long."""
    columns = TurfSettings.__table__.c
    too_long = [
        key for key, value in DEFAULT_SETTINGS.items()
        if isinstance(columns[key].type, String) and columns[key].type.length
        and isinstance(value, str) and len(value) > columns[key].type.length
    ]
    assert too_long == []


def test_every_seed_key_is_a_real_column():
    assert set(DEFAULT_SETTINGS) <= set(TurfSettings.__table__.c.keys())
