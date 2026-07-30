"""add airport last_polled_at throttle

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("airports", sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("airports", "last_polled_at")
