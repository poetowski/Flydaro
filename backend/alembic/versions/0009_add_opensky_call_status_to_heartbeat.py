"""add opensky call status to heartbeat

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("poller_heartbeats", sa.Column("last_opensky_status", sa.Integer(), nullable=True))
    op.add_column("poller_heartbeats", sa.Column("last_opensky_detail", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("poller_heartbeats", "last_opensky_detail")
    op.drop_column("poller_heartbeats", "last_opensky_status")
