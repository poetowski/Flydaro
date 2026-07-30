"""add rental claimed status

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rentals", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.drop_constraint("ck_rentals_status", "rentals")
    op.create_check_constraint(
        "ck_rentals_status",
        "rentals",
        "status in ('PENDING','IN_PROGRESS','RESOLVING','RESOLVED','CLAIMED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_rentals_status", "rentals")
    op.create_check_constraint(
        "ck_rentals_status",
        "rentals",
        "status in ('PENDING','IN_PROGRESS','RESOLVING','RESOLVED')",
    )
    op.drop_column("rentals", "claimed_at")
