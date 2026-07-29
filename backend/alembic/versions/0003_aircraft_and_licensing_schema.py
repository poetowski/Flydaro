"""aircraft types, aircraft registry, airport/aircraft-type unlock tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aircraft_types",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("icao_type_code", sa.String(10), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("manufacturer", sa.String(100), nullable=False),
        sa.Column("is_starter", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("unlock_cost_credits", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_aircraft_types_icao_type_code", "aircraft_types", ["icao_type_code"], unique=True
    )

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

    op.create_table(
        "user_airport_unlocks",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("airport_id", sa.BigInteger(), sa.ForeignKey("airports.id"), primary_key=True),
        sa.Column(
            "unlocked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "user_aircraft_type_unlocks",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column(
            "aircraft_type_id",
            sa.BigInteger(),
            sa.ForeignKey("aircraft_types.id"),
            primary_key=True,
        ),
        sa.Column(
            "unlocked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.add_column(
        "airports",
        sa.Column("unlock_cost_credits", sa.BigInteger(), nullable=False, server_default="0"),
    )

    op.add_column(
        "tracked_flights",
        sa.Column(
            "aircraft_type_id", sa.BigInteger(), sa.ForeignKey("aircraft_types.id"), nullable=True
        ),
    )
    op.create_index(
        "ix_tracked_flights_aircraft_type_id", "tracked_flights", ["aircraft_type_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_tracked_flights_aircraft_type_id", table_name="tracked_flights")
    op.drop_column("tracked_flights", "aircraft_type_id")
    op.drop_column("airports", "unlock_cost_credits")
    op.drop_table("user_aircraft_type_unlocks")
    op.drop_table("user_airport_unlocks")
    op.drop_table("aircraft_registry")
    op.drop_table("aircraft_types")
