"""drop aircraft_registry -- aircraft type now resolves inline from adsb.fi

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_aircraft_registry_aircraft_type_id", table_name="aircraft_registry")
    op.drop_table("aircraft_registry")


def downgrade() -> None:
    op.create_table(
        "aircraft_registry",
        sa.Column("icao24", sa.String(6), primary_key=True),
        sa.Column(
            "aircraft_type_id", sa.BigInteger(), sa.ForeignKey("aircraft_types.id"), nullable=False
        ),
        sa.Column("registration", sa.String(20), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_aircraft_registry_aircraft_type_id", "aircraft_registry", ["aircraft_type_id"]
    )
