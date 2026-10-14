"""turf_settings.default_price_bdt (M4.7)

The price a slot gets when no price band covers it (D-47). Nullable: until the
owner sets prices, the site says "price on request" rather than inventing one.

Revision ID: a4f7c2d9e1b3
Revises: 13a53e9a5687
Create Date: 2026-10-14 12:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'a4f7c2d9e1b3'
down_revision = '13a53e9a5687'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('turf_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_price_bdt', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('turf_settings', schema=None) as batch_op:
        batch_op.drop_column('default_price_bdt')
