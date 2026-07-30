"""retire placeholder cargo items, seed the real Cargo roster

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

RETIRED_CODES = ["PINEAPPLES", "FRAGILE_GOODS"]

# (code, name, flavor_text, settlement_multiplier, base_cost_credits)
NEW_CARGO_ITEMS = [
    (
        "FRUIT_AND_VEGETABLES",
        "Fruit and Vegetables",
        "Fresh produce -- steady demand, modest margins.",
        1.15,
        0,
    ),
    (
        "ELECTRONICS",
        "Electronics",
        "Consumer electronics and components -- higher value, handle with care.",
        1.40,
        100,
    ),
    (
        "MEDICAL",
        "Medical Supplies",
        "Pharmaceuticals and medical equipment -- time-critical and high-value.",
        1.60,
        200,
    ),
]


def upgrade() -> None:
    op.execute(
        "UPDATE item_types SET is_active = false WHERE code IN ("
        + ",".join(f"'{code}'" for code in RETIRED_CODES)
        + ")"
    )

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
                "category": "CARGO",
                "flavor_text": flavor_text,
                "settlement_multiplier": multiplier,
                "base_cost_credits": cost,
                "is_active": True,
            }
            for code, name, flavor_text, multiplier, cost in NEW_CARGO_ITEMS
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM item_types WHERE code IN ("
        + ",".join(f"'{c[0]}'" for c in NEW_CARGO_ITEMS)
        + ")"
    )
    op.execute(
        "UPDATE item_types SET is_active = true WHERE code IN ("
        + ",".join(f"'{code}'" for code in RETIRED_CODES)
        + ")"
    )
