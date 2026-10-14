"""turf_settings.slot_times (M7.7, CR-6)

The owner's 12 slot start times as ["06:00", ...]. NULL means the built-in
default (services/slots.SLOT_TIMES), so existing rows need no data change.

Revision ID: b7e3d1f04a2c
Revises: a4f7c2d9e1b3
Create Date: 2026-10-14 15:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7e3d1f04a2c'
down_revision = 'a4f7c2d9e1b3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('turf_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slot_times', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('turf_settings', schema=None) as batch_op:
        batch_op.drop_column('slot_times')
