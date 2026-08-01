"""balance Passenger roster to match Cargo's 3-tier shape

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

# (code, name, flavor_text, settlement_multiplier, base_cost_credits)
NEW_PASSENGER_ITEMS = [
    (
        "ECONOMY_PASSENGER",
        "Economy Passenger",
        "Budget travelers -- reliable, low-margin business.",
        1.20,
        0,
    ),
    (
        "BUSINESS_PASSENGER",
        "Business Passenger",
        "Comfort seekers paying a premium for space and service.",
        1.50,
        150,
    ),
]


def upgrade() -> None:
    item_types = sa.table(
        "item_types",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("flavor_text", sa.String),
        sa.column("settlement_multiplier", sa.Numeric),
        sa.column("base_cost_credits", sa.BigInteger),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        item_types,
        [
            {
                "code": code,
                "name": name,
                "category": "PASSENGER",
                "flavor_text": flavor_text,
                "settlement_multiplier": multiplier,
                "base_cost_credits": cost,
                "is_active": True,
            }
            for code, name, flavor_text, multiplier, cost in NEW_PASSENGER_ITEMS
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM item_types WHERE code IN ("
        + ",".join(f"'{c[0]}'" for c in NEW_PASSENGER_ITEMS)
        + ")"
    )
