"""aircraft family licensing schema

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

# Original per-type is_starter/unlock_cost_credits from 0004 -- needed to
# restore them correctly on downgrade (by the time this downgrade runs,
# 0016's downgrade has already run first and left exactly these 15 rows,
# with no family_id/is_active changes still pending), rather than leaving
# every row at the blanket column default (false/0).
ORIGINAL_TYPE_VALUES = {
    "A320": (True, 0),
    "A321": (True, 0),
    "B738": (True, 0),
    "B38M": (True, 0),
    "E190": (True, 0),
    "ATR72": (False, 300),
    "B39M": (False, 350),
    "B788": (False, 400),
    "B77W": (False, 400),
    "A359": (False, 450),
    "A388": (False, 500),
    "B744": (False, 500),
    "B748": (False, 550),
    "A124": (False, 650),
    "A339": (False, 600),
}


def upgrade() -> None:
    op.create_table(
        "aircraft_families",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_starter", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("unlock_cost_credits", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_aircraft_families_code", "aircraft_families", ["code"], unique=True)

    op.add_column(
        "aircraft_types",
        sa.Column("family_id", sa.BigInteger(), sa.ForeignKey("aircraft_families.id"), nullable=True),
    )
    op.create_index("ix_aircraft_types_family_id", "aircraft_types", ["family_id"])
    # The "is_active=false OR family_id IS NOT NULL" check constraint is added
    # in 0016, AFTER that migration backfills family_id/is_active -- adding it
    # here would fail immediately, since Postgres validates a new CHECK
    # constraint against every existing row by default, and at this point
    # every row still has family_id=NULL with is_active=true (pre-backfill).

    op.create_table(
        "user_aircraft_family_unlocks",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column(
            "family_id", sa.BigInteger(), sa.ForeignKey("aircraft_families.id"), primary_key=True
        ),
        sa.Column(
            "unlocked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.drop_table("user_aircraft_type_unlocks")

    # Licensing moves to the family level -- these two columns' meaning
    # (is_starter/unlock_cost_credits) now lives on aircraft_families instead.
    op.drop_column("aircraft_types", "is_starter")
    op.drop_column("aircraft_types", "unlock_cost_credits")


def downgrade() -> None:
    op.add_column(
        "aircraft_types",
        sa.Column("unlock_cost_credits", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "aircraft_types",
        sa.Column("is_starter", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    conn = op.get_bind()
    for code, (is_starter, cost) in ORIGINAL_TYPE_VALUES.items():
        conn.execute(
            sa.text(
                "UPDATE aircraft_types SET is_starter = :is_starter, unlock_cost_credits = :cost "
                "WHERE icao_type_code = :code"
            ),
            {"is_starter": is_starter, "cost": cost, "code": code},
        )

    op.create_table(
        "user_aircraft_type_unlocks",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column(
            "aircraft_type_id", sa.BigInteger(), sa.ForeignKey("aircraft_types.id"), primary_key=True
        ),
        sa.Column(
            "unlocked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    # Note: any user_aircraft_family_unlocks rows are not restorable into
    # user_aircraft_type_unlocks -- the two aren't equivalent (family vs
    # type granularity), same acceptable-data-loss precedent as elsewhere
    # in this migration history.

    op.drop_index("ix_aircraft_types_family_id", table_name="aircraft_types")
    op.drop_column("aircraft_types", "family_id")

    op.drop_table("user_aircraft_family_unlocks")
    op.drop_index("ix_aircraft_families_code", table_name="aircraft_families")
    op.drop_table("aircraft_families")
