"""reframe betting as capacity rental; cargo types become categorized item types

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- bets -> rentals ---
    op.rename_table("bets", "rentals")
    op.alter_column("rentals", "cargo_type_id", new_column_name="item_type_id")
    op.alter_column("rentals", "stake_credits", new_column_name="rental_fee_credits")
    op.alter_column("rentals", "placed_at", new_column_name="rented_at")
    op.alter_column("rentals", "payout_credits", new_column_name="settlement_credits")
    op.alter_column("rentals", "payout_breakdown", new_column_name="settlement_breakdown")

    op.execute("ALTER INDEX ix_bets_user_id RENAME TO ix_rentals_user_id")
    op.execute("ALTER INDEX ix_bets_tracked_flight_id RENAME TO ix_rentals_tracked_flight_id")
    op.execute("ALTER TABLE rentals RENAME CONSTRAINT ck_bets_status TO ck_rentals_status")
    op.execute(
        "ALTER TABLE rentals RENAME CONSTRAINT ck_bets_stake_positive "
        "TO ck_rentals_rental_fee_positive"
    )

    # --- cargo_types -> item_types, plus new category column ---
    op.rename_table("cargo_types", "item_types")
    op.alter_column("item_types", "payout_multiplier", new_column_name="settlement_multiplier")
    op.execute("ALTER INDEX ix_cargo_types_code RENAME TO ix_item_types_code")

    op.add_column("item_types", sa.Column("category", sa.String(20), nullable=True))
    # Recategorize the 3 existing items -- placeholders until the real
    # Cargo/Passenger roster is specified; VIP Passenger is the obvious
    # Passenger-category item, the other two are obviously Cargo.
    op.execute("UPDATE item_types SET category = 'PASSENGER' WHERE code = 'VIP_PASSENGER'")
    op.execute("UPDATE item_types SET category = 'CARGO' WHERE category IS NULL")
    op.alter_column("item_types", "category", nullable=False)
    op.create_check_constraint(
        "ck_item_types_category", "item_types", "category in ('CARGO','PASSENGER')"
    )

    # --- wallet_ledger: rename related_bet_id, rewrite/rename reason values ---
    op.execute("UPDATE wallet_ledger SET reason = 'rental_fee' WHERE reason = 'bet_stake'")
    op.execute("UPDATE wallet_ledger SET reason = 'settlement' WHERE reason = 'bet_payout'")
    op.execute(
        "UPDATE wallet_ledger SET reason = 'item_type_purchase' WHERE reason = 'cargo_purchase'"
    )
    op.drop_constraint("ck_wallet_ledger_reason", "wallet_ledger")
    op.create_check_constraint(
        "ck_wallet_ledger_reason",
        "wallet_ledger",
        "reason in ('signup_bonus','rental_fee','settlement','license_purchase',"
        "'item_type_purchase','admin_adjustment')",
    )
    op.alter_column("wallet_ledger", "related_bet_id", new_column_name="related_rental_id")

    # --- tracked_flights: bets_open -> capacity_open ---
    op.alter_column("tracked_flights", "bets_open", new_column_name="capacity_open")


def downgrade() -> None:
    op.alter_column("tracked_flights", "capacity_open", new_column_name="bets_open")

    op.alter_column("wallet_ledger", "related_rental_id", new_column_name="related_bet_id")
    op.drop_constraint("ck_wallet_ledger_reason", "wallet_ledger")
    op.create_check_constraint(
        "ck_wallet_ledger_reason",
        "wallet_ledger",
        "reason in ('signup_bonus','bet_stake','bet_payout','license_purchase',"
        "'cargo_purchase','admin_adjustment')",
    )
    op.execute("UPDATE wallet_ledger SET reason = 'bet_stake' WHERE reason = 'rental_fee'")
    op.execute("UPDATE wallet_ledger SET reason = 'bet_payout' WHERE reason = 'settlement'")
    op.execute(
        "UPDATE wallet_ledger SET reason = 'cargo_purchase' WHERE reason = 'item_type_purchase'"
    )

    op.drop_constraint("ck_item_types_category", "item_types")
    op.drop_column("item_types", "category")
    op.execute("ALTER INDEX ix_item_types_code RENAME TO ix_cargo_types_code")
    op.alter_column("item_types", "settlement_multiplier", new_column_name="payout_multiplier")
    op.rename_table("item_types", "cargo_types")

    op.execute(
        "ALTER TABLE rentals RENAME CONSTRAINT ck_rentals_rental_fee_positive "
        "TO ck_bets_stake_positive"
    )
    op.execute("ALTER TABLE rentals RENAME CONSTRAINT ck_rentals_status TO ck_bets_status")
    op.execute("ALTER INDEX ix_rentals_tracked_flight_id RENAME TO ix_bets_tracked_flight_id")
    op.execute("ALTER INDEX ix_rentals_user_id RENAME TO ix_bets_user_id")

    op.alter_column("rentals", "settlement_breakdown", new_column_name="payout_breakdown")
    op.alter_column("rentals", "settlement_credits", new_column_name="payout_credits")
    op.alter_column("rentals", "rented_at", new_column_name="placed_at")
    op.alter_column("rentals", "rental_fee_credits", new_column_name="stake_credits")
    op.alter_column("rentals", "item_type_id", new_column_name="cargo_type_id")
    op.rename_table("rentals", "bets")
