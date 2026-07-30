"""drop poller_heartbeats table

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("poller_heartbeats")


def downgrade() -> None:
    op.create_table(
        "poller_heartbeats",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("credits_remaining", sa.Integer(), nullable=True),
        sa.Column("last_opensky_status", sa.Integer(), nullable=True),
        sa.Column("last_opensky_detail", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
