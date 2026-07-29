"""initial schema: auth, airports, cargo types, tracked flights, wallet, bets

Revision ID: 0001
Revises:
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", sa.BigInteger(), sa.ForeignKey("refresh_tokens.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "airports",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("icao4", sa.String(4), nullable=False),
        sa.Column("iata", sa.String(3), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("bbox_lamin", sa.Float(), nullable=False),
        sa.Column("bbox_lomin", sa.Float(), nullable=False),
        sa.Column("bbox_lamax", sa.Float(), nullable=False),
        sa.Column("bbox_lomax", sa.Float(), nullable=False),
        sa.Column("is_starter", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_airports_icao4", "airports", ["icao4"], unique=True)

    op.create_table(
        "cargo_types",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("flavor_text", sa.String(500), nullable=False),
        sa.Column("payout_multiplier", sa.Numeric(5, 2), nullable=False),
        sa.Column("base_cost_credits", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_cargo_types_code", "cargo_types", ["code"], unique=True)

    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.create_table(
        "tracked_flights",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("icao24", sa.String(6), nullable=False),
        sa.Column("callsign", sa.String(20), nullable=True),
        sa.Column("origin_airport_id", sa.BigInteger(), sa.ForeignKey("airports.id"), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_seen_lat", sa.Float(), nullable=False),
        sa.Column("first_seen_lon", sa.Float(), nullable=False),
        sa.Column("first_seen_alt", sa.Float(), nullable=True),
        sa.Column("first_seen_velocity", sa.Float(), nullable=True),
        sa.Column("first_seen_vertical_rate", sa.Float(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_lat", sa.Float(), nullable=True),
        sa.Column("last_seen_lon", sa.Float(), nullable=True),
        sa.Column("last_seen_alt", sa.Float(), nullable=True),
        sa.Column("last_seen_velocity", sa.Float(), nullable=True),
        sa.Column("last_seen_vertical_rate", sa.Float(), nullable=True),
        sa.Column("last_seen_on_ground", sa.Boolean(), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="AIRBORNE_OPEN",
        ),
        sa.Column("bets_open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("landing_suspected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_summary", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status in ('AIRBORNE_OPEN','AIRBORNE_LOCKED','LANDING_SUSPECTED',"
            "'RESOLVED_LANDED','RESOLVED_TIMEOUT','RESOLVED_LOST_SIGNAL')",
            name="ck_tracked_flights_status",
        ),
    )
    op.create_index("ix_tracked_flights_icao24", "tracked_flights", ["icao24"])
    op.execute(
        """
        CREATE UNIQUE INDEX ix_tracked_flights_open_icao24
        ON tracked_flights (icao24)
        WHERE status NOT IN ('RESOLVED_LANDED', 'RESOLVED_TIMEOUT', 'RESOLVED_LOST_SIGNAL')
        """
    )

    op.create_table(
        "flight_state_samples",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("tracked_flight_id", sa.BigInteger(), sa.ForeignKey("tracked_flights.id"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("baro_altitude", sa.Float(), nullable=True),
        sa.Column("velocity", sa.Float(), nullable=True),
        sa.Column("vertical_rate", sa.Float(), nullable=True),
        sa.Column("on_ground", sa.Boolean(), nullable=True),
        sa.Column("raw", json_type, nullable=True),
    )
    op.create_index("ix_flight_state_samples_tracked_flight_id", "flight_state_samples", ["tracked_flight_id"])

    op.create_table(
        "wallets",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("balance_credits", sa.BigInteger(), nullable=False, server_default="0"),
        sa.CheckConstraint("balance_credits >= 0", name="ck_wallet_balance_nonneg"),
    )

    op.create_table(
        "bets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tracked_flight_id", sa.BigInteger(), sa.ForeignKey("tracked_flights.id"), nullable=False),
        sa.Column("cargo_type_id", sa.BigInteger(), sa.ForeignKey("cargo_types.id"), nullable=False),
        sa.Column("stake_credits", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("placed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payout_credits", sa.BigInteger(), nullable=True),
        sa.Column("payout_breakdown", json_type, nullable=True),
        sa.Column("resolution_reason", sa.String(50), nullable=True),
        sa.CheckConstraint(
            "status in ('PENDING','IN_PROGRESS','RESOLVING','RESOLVED')",
            name="ck_bets_status",
        ),
        sa.CheckConstraint("stake_credits > 0", name="ck_bets_stake_positive"),
    )
    op.create_index("ix_bets_user_id", "bets", ["user_id"])
    op.create_index("ix_bets_tracked_flight_id", "bets", ["tracked_flight_id"])

    op.create_table(
        "wallet_ledger",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("delta_credits", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("related_bet_id", sa.BigInteger(), sa.ForeignKey("bets.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "reason in ('signup_bonus','bet_stake','bet_payout','license_purchase',"
            "'cargo_purchase','admin_adjustment')",
            name="ck_wallet_ledger_reason",
        ),
    )
    op.create_index("ix_wallet_ledger_user_id", "wallet_ledger", ["user_id"])


def downgrade() -> None:
    op.drop_table("wallet_ledger")
    op.drop_table("bets")
    op.drop_table("wallets")
    op.drop_table("flight_state_samples")
    op.execute("DROP INDEX IF EXISTS ix_tracked_flights_open_icao24")
    op.drop_table("tracked_flights")
    op.drop_table("cargo_types")
    op.drop_table("airports")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
