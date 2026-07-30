"""drop underused locked airports (20 -> 10 total)

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

BBOX_MARGIN = 1.0

# Dropped entirely: kept 5 are KJFK, LFPG, RJTT, LTFM, WSSS (unchanged, not
# touched by this migration). (icao4, iata, name, city, country, lat, lon,
# unlock_cost_credits) -- exact values from 0004, needed to restore on downgrade.
DROPPED_AIRPORTS = [
    ("KLAX", "LAX", "Los Angeles Intl", "Los Angeles", "United States", 33.9416, -118.4085, 450),
    ("CYYZ", "YYZ", "Toronto Pearson", "Toronto", "Canada", 43.6777, -79.6248, 350),
    ("LEMD", "MAD", "Madrid Barajas", "Madrid", "Spain", 40.4983, -3.5676, 400),
    ("LIRF", "FCO", "Rome Fiumicino", "Rome", "Italy", 41.8003, 12.2389, 450),
    ("EDDM", "MUC", "Munich", "Munich", "Germany", 48.3538, 11.7861, 350),
    ("EKCH", "CPH", "Copenhagen Kastrup", "Copenhagen", "Denmark", 55.6180, 12.6508, 350),
    ("SBGR", "GRU", "Sao Paulo/Guarulhos", "Sao Paulo", "Brazil", -23.4356, -46.4731, 600),
    ("FAOR", "JNB", "OR Tambo", "Johannesburg", "South Africa", -26.1392, 28.2460, 700),
    ("VABB", "BOM", "Chhatrapati Shivaji", "Mumbai", "India", 19.0887, 72.8679, 650),
    ("YSSY", "SYD", "Sydney Kingsford Smith", "Sydney", "Australia", -33.9399, 151.1753, 800),
]


def upgrade() -> None:
    icao4_list = ",".join(f"'{a[0]}'" for a in DROPPED_AIRPORTS)
    # No FK cascade: if a tracked_flights row still references one of these
    # airports, the DELETE FROM airports below fails on the FK constraint --
    # a deliberate signal to go look, not something to silently work around
    # by reaching into flight/rental/ledger history.
    op.execute(
        f"DELETE FROM user_airport_unlocks WHERE airport_id IN "
        f"(SELECT id FROM airports WHERE icao4 IN ({icao4_list}))"
    )
    op.execute(f"DELETE FROM airports WHERE icao4 IN ({icao4_list})")


def downgrade() -> None:
    # Restores the 10 airport rows (matching 0004's exact values); any
    # user_airport_unlocks rows deleted by upgrade() are not restorable,
    # same precedent as 0004's own hard-delete downgrade.
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
        sa.column("unlock_cost_credits", sa.BigInteger),
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
                "is_starter": False,
                "is_active": False,
                "unlock_cost_credits": cost,
            }
            for icao4, iata, name, city, country, lat, lon, cost in DROPPED_AIRPORTS
        ],
    )
