"""rename rental status PENDING to FLYING

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-01

"""
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the constraint first -- it doesn't allow 'FLYING' yet, so the
    # backfill below would violate it if run while still active.
    op.drop_constraint("ck_rentals_status", "rentals")
    op.execute("UPDATE rentals SET status = 'FLYING' WHERE status = 'PENDING'")
    op.create_check_constraint(
        "ck_rentals_status",
        "rentals",
        "status in ('FLYING','IN_PROGRESS','RESOLVING','RESOLVED','CLAIMED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_rentals_status", "rentals")
    op.execute("UPDATE rentals SET status = 'PENDING' WHERE status = 'FLYING'")
    op.create_check_constraint(
        "ck_rentals_status",
        "rentals",
        "status in ('PENDING','IN_PROGRESS','RESOLVING','RESOLVED','CLAIMED')",
    )
