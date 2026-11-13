"""The client's details for launch (2026-11-13): the bKash merchant number, the three
period prices (Morning 1000, Afternoon 1500, Night 1800 per hour) and the Google Maps pin.

Data only, no schema change. Each value is written ONLY where the setting is still empty
(or still a TODO placeholder), so anything the owner already saved in Settings stays.
Does nothing on a database without a settings row (seed-settings creates it later).
The owner can change all of it afterwards: bKash number and prices in Settings, the map
by asking the developer (D-23).

Revision ID: e8a2c4f6b1d3
Revises: d5e1a7c3b9f2
Create Date: 2026-11-13 20:00:00

"""
import json

from alembic import op
import sqlalchemy as sa


revision = 'e8a2c4f6b1d3'
down_revision = 'd5e1a7c3b9f2'
branch_labels = None
depends_on = None

BKASH_NUMBER = "01827881299"
PRICES = {"morning": 1000, "afternoon": 1500, "night": 1800}
MAP_LINK = "https://maps.app.goo.gl/aDJKZxWBbtHC5p6E7?g_st=aw"  # the owner's share link
MAP_EMBED_URL = "https://www.google.com/maps/embed?origin=mfe&pb=!1m3!2m1!1sT+Turf+Zone,+2C42%2BWQ9,+Feni!6i17"  # same pin

settings = sa.table(
    "turf_settings",
    sa.column("id", sa.Integer),
    sa.column("bkash_number", sa.String),
    sa.column("pricing", sa.Text),
    sa.column("map_link", sa.Text),
    sa.column("map_embed_url", sa.Text),
)


def _empty(value) -> bool:
    return not value or "TODO" in value or not value.strip()


def _prices_set(raw) -> bool:
    """True when pricing already holds a whole-taka price for each period (D-53)."""
    try:
        pricing = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return False
    return isinstance(pricing, dict) and all(isinstance(pricing.get(k), int) for k in PRICES)


def upgrade():
    bind = op.get_bind()
    row = bind.execute(sa.select(settings).where(settings.c.id == 1)).first()
    if row is None:
        return
    changes = {}
    if _empty(row.bkash_number):
        changes["bkash_number"] = BKASH_NUMBER
    if not _prices_set(row.pricing):
        changes["pricing"] = json.dumps(PRICES)
    if _empty(row.map_link):
        changes["map_link"] = MAP_LINK
    if _empty(row.map_embed_url):
        changes["map_embed_url"] = MAP_EMBED_URL
    if changes:
        bind.execute(settings.update().where(settings.c.id == 1).values(**changes))


def downgrade():
    pass  # data, not schema: going back leaves the owner's settings as they are
