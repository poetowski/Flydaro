"""seed starter airports and cargo types

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# (icao4, iata, name, city, country, lat, lon)
# Bounding box is +/- 0.35 degrees around the airport reference point --
# wide enough to catch initial climb-out, tight enough to keep OpenSky
# credit usage per poll low. Tune empirically per plan's open risks.
BBOX_MARGIN = 0.35

STARTER_AIRPORTS = [
    ("EHAM", "AMS", "Amsterdam Schiphol", "Amsterdam", "Netherlands", 52.3086, 4.7639),
    ("EDDF", "FRA", "Frankfurt am Main", "Frankfurt", "Germany", 50.0379, 8.5622),
    ("EGLL", "LHR", "London Heathrow", "London", "United Kingdom", 51.4700, -0.4543),
    ("KATL", "ATL", "Hartsfield-Jackson Atlanta", "Atlanta", "United States", 33.6407, -84.4277),
    ("OMDB", "DXB", "Dubai International", "Dubai", "United Arab Emirates", 25.2532, 55.3657),
]

CARGO_TYPES = [
    ("PINEAPPLES", "Pineapples", "A crate of pineapples. Nothing can go wrong.", 1.10, 0),
    ("FRAGILE_GOODS", "Fragile Goods", "Handle with care -- delays and diversions hurt more here.", 1.35, 100),
    ("VIP_PASSENGER", "VIP Passenger", "High-value, high-stakes. Big payouts, less forgiving of hiccups.", 1.75, 250),
]


def upgrade() -> None:
    airports = sa.table(
        "airports",
        sa.column("icao4", sa.String),
        sa.column("iata", sa.String),
        sa.column("name", sa.String),
        sa.column("city", sa.String),
        sa.column("country", sa.String),
        sa.column("lat", sa.Float),
        sa.column("lon", sa.Float),
        sa.column("bbox_lamin", sa.Float),
        sa.column("bbox_lomin", sa.Float),
        sa.column("bbox_lamax", sa.Float),
        sa.column("bbox_lomax", sa.Float),
        sa.column("is_starter", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        airports,
        [
            {
                "icao4": icao4,
                "iata": iata,
                "name": name,
                "city": city,
                "country": country,
                "lat": lat,
                "lon": lon,
                "bbox_lamin": lat - BBOX_MARGIN,
                "bbox_lomin": lon - BBOX_MARGIN,
                "bbox_lamax": lat + BBOX_MARGIN,
                "bbox_lomax": lon + BBOX_MARGIN,
                "is_starter": True,
                "is_active": True,
            }
            for icao4, iata, name, city, country, lat, lon in STARTER_AIRPORTS
        ],
    )

    cargo_types = sa.table(
        "cargo_types",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("flavor_text", sa.String),
        sa.column("payout_multiplier", sa.Numeric),
        sa.column("base_cost_credits", sa.BigInteger),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        cargo_types,
        [
            {
                "code": code,
                "name": name,
                "flavor_text": flavor_text,
                "payout_multiplier": multiplier,
                "base_cost_credits": cost,
                "is_active": True,
            }
            for code, name, flavor_text, multiplier, cost in CARGO_TYPES
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM cargo_types WHERE code IN ("
        + ",".join(f"'{c[0]}'" for c in CARGO_TYPES)
        + ")"
    )
    op.execute(
        "DELETE FROM airports WHERE icao4 IN ("
        + ",".join(f"'{a[0]}'" for a in STARTER_AIRPORTS)
        + ")"
    )
