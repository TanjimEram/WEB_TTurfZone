"""admins.email + admins.reset_sent_at, login_failures table (M5.10, D-51)

Revision ID: c3d9e2f1a7b5
Revises: b7e3d1f04a2c
Create Date: 2026-11-08 12:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d9e2f1a7b5'
down_revision = 'b7e3d1f04a2c'
branch_labels = None
depends_on = None

MYSQL = {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci", "mysql_engine": "InnoDB"}


def upgrade():
    with op.batch_alter_table('admins', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=254), nullable=True))
        batch_op.add_column(sa.Column('reset_sent_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        'login_failures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ip', sa.String(length=45), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        **MYSQL,
    )
    op.create_index('ix_login_failures_ip_created', 'login_failures', ['ip', 'created_at'], unique=False)


def downgrade():
    op.drop_index('ix_login_failures_ip_created', table_name='login_failures')
    op.drop_table('login_failures')
    with op.batch_alter_table('admins', schema=None) as batch_op:
        batch_op.drop_column('reset_sent_at')
        batch_op.drop_column('email')
