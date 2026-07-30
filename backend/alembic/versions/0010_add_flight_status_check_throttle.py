"""add tracked_flights.last_status_check_at

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tracked_flights", sa.Column("last_status_check_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("tracked_flights", "last_status_check_at")
