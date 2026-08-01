"""add per-airport crew mechanic

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_airport_crew",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("airport_id", sa.BigInteger(), sa.ForeignKey("airports.id"), primary_key=True),
        sa.Column("crew_count", sa.BigInteger(), nullable=False, server_default="0"),
    )

    op.drop_constraint("ck_wallet_ledger_reason", "wallet_ledger")
    op.create_check_constraint(
        "ck_wallet_ledger_reason",
        "wallet_ledger",
        "reason in ('signup_bonus','rental_fee','settlement','license_purchase',"
        "'item_type_purchase','admin_adjustment','crew_hire')",
    )

    # Starter crew: every existing user gets the same 1 crew member at
    # Dubai and 1 at Frankfurt that new signups get (see auth_service.signup).
    op.execute(
        """
        INSERT INTO user_airport_crew (user_id, airport_id, crew_count)
        SELECT u.id, a.id, 1
        FROM users u, airports a
        WHERE a.icao4 IN ('OMDB', 'EDDF')
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_wallet_ledger_reason", "wallet_ledger")
    op.create_check_constraint(
        "ck_wallet_ledger_reason",
        "wallet_ledger",
        "reason in ('signup_bonus','rental_fee','settlement','license_purchase',"
        "'item_type_purchase','admin_adjustment')",
    )
    op.drop_table("user_airport_crew")
