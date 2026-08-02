"""recalibrate economy prices (~2x) and align item minimums to slider marks

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-02

"""
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE airports SET unlock_cost_credits = 800 WHERE icao4 = 'KJFK'")
    op.execute("UPDATE airports SET unlock_cost_credits = 800 WHERE icao4 = 'LFPG'")
    op.execute("UPDATE airports SET unlock_cost_credits = 1000 WHERE icao4 = 'LTFM'")
    op.execute("UPDATE airports SET unlock_cost_credits = 1200 WHERE icao4 = 'WSSS'")
    op.execute("UPDATE airports SET unlock_cost_credits = 1400 WHERE icao4 = 'RJTT'")

    op.execute(
        "UPDATE aircraft_families SET unlock_cost_credits = 700 WHERE code = 'EMBRAER_EJET_FAMILY'"
    )
    op.execute("UPDATE aircraft_families SET unlock_cost_credits = 700 WHERE code = 'CRJ_FAMILY'")
    op.execute("UPDATE aircraft_families SET unlock_cost_credits = 1100 WHERE code = 'B777_FAMILY'")
    op.execute("UPDATE aircraft_families SET unlock_cost_credits = 1200 WHERE code = 'B787_FAMILY'")

    op.execute("UPDATE item_types SET base_cost_credits = 250 WHERE code = 'BUSINESS_PASSENGER'")
    op.execute("UPDATE item_types SET base_cost_credits = 500 WHERE code = 'MEDICAL'")
    op.execute("UPDATE item_types SET base_cost_credits = 1000 WHERE code = 'VIP_PASSENGER'")
    # ELECTRONICS stays 100 -- already matches its target slider mark, no row change needed.


def downgrade() -> None:
    op.execute("UPDATE airports SET unlock_cost_credits = 400 WHERE icao4 = 'KJFK'")
    op.execute("UPDATE airports SET unlock_cost_credits = 400 WHERE icao4 = 'LFPG'")
    op.execute("UPDATE airports SET unlock_cost_credits = 500 WHERE icao4 = 'LTFM'")
    op.execute("UPDATE airports SET unlock_cost_credits = 600 WHERE icao4 = 'WSSS'")
    op.execute("UPDATE airports SET unlock_cost_credits = 700 WHERE icao4 = 'RJTT'")

    op.execute(
        "UPDATE aircraft_families SET unlock_cost_credits = 350 WHERE code = 'EMBRAER_EJET_FAMILY'"
    )
    op.execute("UPDATE aircraft_families SET unlock_cost_credits = 350 WHERE code = 'CRJ_FAMILY'")
    op.execute("UPDATE aircraft_families SET unlock_cost_credits = 550 WHERE code = 'B777_FAMILY'")
    op.execute("UPDATE aircraft_families SET unlock_cost_credits = 600 WHERE code = 'B787_FAMILY'")

    op.execute("UPDATE item_types SET base_cost_credits = 150 WHERE code = 'BUSINESS_PASSENGER'")
    op.execute("UPDATE item_types SET base_cost_credits = 200 WHERE code = 'MEDICAL'")
    op.execute("UPDATE item_types SET base_cost_credits = 250 WHERE code = 'VIP_PASSENGER'")
