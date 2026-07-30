"""seed locked airports and aircraft types (pilot licenses)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-29

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

# Same convention as 0002. Widened in 0007 (both here and for already-seeded
# rows) to match the extended takeoff-detection window in thresholds.py.
BBOX_MARGIN = 1.0

# (icao4, iata, name, city, country, lat, lon, unlock_cost_credits)
LOCKED_AIRPORTS = [
    ("KJFK", "JFK", "John F. Kennedy Intl", "New York", "United States", 40.6413, -73.7781, 400),
    ("KLAX", "LAX", "Los Angeles Intl", "Los Angeles", "United States", 33.9416, -118.4085, 450),
    ("CYYZ", "YYZ", "Toronto Pearson", "Toronto", "Canada", 43.6777, -79.6248, 350),
    ("LFPG", "CDG", "Paris Charles de Gaulle", "Paris", "France", 49.0097, 2.5479, 400),
    ("LEMD", "MAD", "Madrid Barajas", "Madrid", "Spain", 40.4983, -3.5676, 400),
    ("LIRF", "FCO", "Rome Fiumicino", "Rome", "Italy", 41.8003, 12.2389, 450),
    ("EDDM", "MUC", "Munich", "Munich", "Germany", 48.3538, 11.7861, 350),
    ("EKCH", "CPH", "Copenhagen Kastrup", "Copenhagen", "Denmark", 55.6180, 12.6508, 350),
    ("LTFM", "IST", "Istanbul Airport", "Istanbul", "Turkey", 41.2753, 28.7519, 500),
    ("SBGR", "GRU", "Sao Paulo/Guarulhos", "Sao Paulo", "Brazil", -23.4356, -46.4731, 600),
    ("FAOR", "JNB", "OR Tambo", "Johannesburg", "South Africa", -26.1392, 28.2460, 700),
    ("VABB", "BOM", "Chhatrapati Shivaji", "Mumbai", "India", 19.0887, 72.8679, 650),
    ("WSSS", "SIN", "Singapore Changi", "Singapore", "Singapore", 1.3644, 103.9915, 600),
    ("RJTT", "HND", "Tokyo Haneda", "Tokyo", "Japan", 35.5494, 139.7798, 700),
    ("YSSY", "SYD", "Sydney Kingsford Smith", "Sydney", "Australia", -33.9399, 151.1753, 800),
]

# (icao_type_code, name, manufacturer, is_starter, unlock_cost_credits)
AIRCRAFT_TYPES = [
    ("A320", "Airbus A320", "Airbus", True, 0),
    ("A321", "Airbus A321", "Airbus", True, 0),
    ("B738", "Boeing 737-800", "Boeing", True, 0),
    ("B38M", "Boeing 737 MAX 8", "Boeing", True, 0),
    ("E190", "Embraer E190", "Embraer", True, 0),
    ("ATR72", "ATR 72", "ATR", False, 300),
    ("B39M", "Boeing 737 MAX 9", "Boeing", False, 350),
    ("B788", "Boeing 787-8 Dreamliner", "Boeing", False, 400),
    ("B77W", "Boeing 777-300ER", "Boeing", False, 400),
    ("A359", "Airbus A350-900", "Airbus", False, 450),
    ("A388", "Airbus A380-800", "Airbus", False, 500),
    ("B744", "Boeing 747-400", "Boeing", False, 500),
    ("B748", "Boeing 747-8", "Boeing", False, 550),
    ("A124", "Antonov An-124", "Antonov", False, 650),
    ("A339", "Airbus A330-900", "Airbus", False, 600),
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
                # Not polled until some player unlocks it -- see
                # license_service.unlock_airport(), which flips this True.
                "is_active": False,
                "unlock_cost_credits": cost,
            }
            for icao4, iata, name, city, country, lat, lon, cost in LOCKED_AIRPORTS
        ],
    )

    aircraft_types = sa.table(
        "aircraft_types",
        sa.column("icao_type_code", sa.String),
        sa.column("name", sa.String),
        sa.column("manufacturer", sa.String),
        sa.column("is_starter", sa.Boolean),
        sa.column("unlock_cost_credits", sa.BigInteger),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        aircraft_types,
        [
            {
                "icao_type_code": code,
                "name": name,
                "manufacturer": manufacturer,
                "is_starter": is_starter,
                "unlock_cost_credits": cost,
                "is_active": True,
            }
            for code, name, manufacturer, is_starter, cost in AIRCRAFT_TYPES
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM aircraft_types WHERE icao_type_code IN ("
        + ",".join(f"'{t[0]}'" for t in AIRCRAFT_TYPES)
        + ")"
    )
    op.execute(
        "DELETE FROM airports WHERE icao4 IN ("
        + ",".join(f"'{a[0]}'" for a in LOCKED_AIRPORTS)
        + ")"
    )
