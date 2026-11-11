"""CR-9: bookings carry the customer's email, bKash payer number and a unique TrxID;
turf_settings carries the bKash merchant number and the advance amount.

Does not touch the one-booking-per-slot rule (uq_active_slot / active_slot_key, D-42):
PENDING was already an active status.

Revision ID: d5e1a7c3b9f2
Revises: c3d9e2f1a7b5
Create Date: 2026-11-11 18:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'd5e1a7c3b9f2'
down_revision = 'c3d9e2f1a7b5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('customer_email', sa.String(length=254), nullable=True))
        batch_op.add_column(sa.Column('payer_number', sa.String(length=14), nullable=True))
        batch_op.add_column(sa.Column('trx_id', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('email_sent_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('uq_bookings_trx_id', ['trx_id'], unique=True)
    with op.batch_alter_table('turf_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bkash_number', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('advance_bdt', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('turf_settings', schema=None) as batch_op:
        batch_op.drop_column('advance_bdt')
        batch_op.drop_column('bkash_number')
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.drop_index('uq_bookings_trx_id')
        batch_op.drop_column('email_sent_at')
        batch_op.drop_column('trx_id')
        batch_op.drop_column('payer_number')
        batch_op.drop_column('customer_email')
