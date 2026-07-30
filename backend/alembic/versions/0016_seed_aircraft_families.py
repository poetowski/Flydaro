"""seed aircraft families, reassign/retire/insert aircraft_types

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-30

"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

# (code, name, is_starter, unlock_cost_credits) -- data-driven per real
# OpenSky traffic sampling, see the plan doc for the frequency analysis.
FAMILIES = [
    ("A320_FAMILY", "Airbus A320 Family", True, 0),
    ("B737_FAMILY", "Boeing 737 Family", True, 0),
    ("EMBRAER_EJET_FAMILY", "Embraer E-Jet/ERJ Family", False, 350),
    ("CRJ_FAMILY", "Bombardier CRJ Family", False, 350),
    ("B777_FAMILY", "Boeing 777 Family", False, 550),
    ("B787_FAMILY", "Boeing 787 Dreamliner Family", False, 600),
]

# icao_type_code -> family code, for the 8 already-seeded types being reused as-is.
REUSED_TYPE_FAMILY = {
    "A320": "A320_FAMILY",
    "A321": "A320_FAMILY",
    "B738": "B737_FAMILY",
    "B38M": "B737_FAMILY",
    "B39M": "B737_FAMILY",
    "E190": "EMBRAER_EJET_FAMILY",
    "B788": "B787_FAMILY",
    "B77W": "B777_FAMILY",
}

# Retired: no family, is_active=false -- ranked below all 6 chosen families
# by real observed frequency (see plan doc); dropped from the licensable catalog.
RETIRED_TYPE_CODES = ["ATR72", "A359", "A388", "B744", "B748", "A124", "A339"]

# (icao_type_code, name, manufacturer, family_code) -- newly seeded types,
# display names are cosmetic-only (matching is by icao_type_code).
NEW_TYPES = [
    ("A318", "Airbus A318", "Airbus", "A320_FAMILY"),
    ("A319", "Airbus A319", "Airbus", "A320_FAMILY"),
    ("A20N", "Airbus A320neo", "Airbus", "A320_FAMILY"),
    ("A21N", "Airbus A321neo", "Airbus", "A320_FAMILY"),
    ("B734", "Boeing 737-400", "Boeing", "B737_FAMILY"),
    ("B735", "Boeing 737-500", "Boeing", "B737_FAMILY"),
    ("B736", "Boeing 737-600", "Boeing", "B737_FAMILY"),
    ("B737", "Boeing 737-700", "Boeing", "B737_FAMILY"),
    ("B739", "Boeing 737-900", "Boeing", "B737_FAMILY"),
    ("B37M", "Boeing 737 MAX 7", "Boeing", "B737_FAMILY"),
    ("E135", "Embraer ERJ-135", "Embraer", "EMBRAER_EJET_FAMILY"),
    ("E145", "Embraer ERJ-145", "Embraer", "EMBRAER_EJET_FAMILY"),
    ("E170", "Embraer E170", "Embraer", "EMBRAER_EJET_FAMILY"),
    ("E175", "Embraer E175", "Embraer", "EMBRAER_EJET_FAMILY"),
    ("E195", "Embraer E195", "Embraer", "EMBRAER_EJET_FAMILY"),
    ("E75L", "Embraer E175 (Long Wing)", "Embraer", "EMBRAER_EJET_FAMILY"),
    ("E75S", "Embraer E175 (Short Wing)", "Embraer", "EMBRAER_EJET_FAMILY"),
    ("E290", "Embraer E190-E2", "Embraer", "EMBRAER_EJET_FAMILY"),
    ("E295", "Embraer E195-E2", "Embraer", "EMBRAER_EJET_FAMILY"),
    ("CRJ2", "Bombardier CRJ200", "Bombardier", "CRJ_FAMILY"),
    ("CRJ7", "Bombardier CRJ700", "Bombardier", "CRJ_FAMILY"),
    ("CRJ9", "Bombardier CRJ900", "Bombardier", "CRJ_FAMILY"),
    ("CRJX", "Bombardier CRJ1000", "Bombardier", "CRJ_FAMILY"),
    ("CL60", "Bombardier Challenger 600", "Bombardier", "CRJ_FAMILY"),
    ("B772", "Boeing 777-200", "Boeing", "B777_FAMILY"),
    ("B773", "Boeing 777-300", "Boeing", "B777_FAMILY"),
    ("B77L", "Boeing 777-200LR/Freighter", "Boeing", "B777_FAMILY"),
    ("B789", "Boeing 787-9", "Boeing", "B787_FAMILY"),
    ("B78X", "Boeing 787-10", "Boeing", "B787_FAMILY"),
]


def upgrade() -> None:
    conn = op.get_bind()

    family_ids: dict[str, int] = {}
    for code, name, is_starter, cost in FAMILIES:
        result = conn.execute(
            sa.text(
                "INSERT INTO aircraft_families (code, name, is_starter, unlock_cost_credits, is_active) "
                "VALUES (:code, :name, :is_starter, :cost, true) RETURNING id"
            ),
            {"code": code, "name": name, "is_starter": is_starter, "cost": cost},
        )
        family_ids[code] = result.scalar_one()

    for type_code, family_code in REUSED_TYPE_FAMILY.items():
        conn.execute(
            sa.text("UPDATE aircraft_types SET family_id = :family_id WHERE icao_type_code = :code"),
            {"family_id": family_ids[family_code], "code": type_code},
        )

    retired_list = ",".join(f"'{c}'" for c in RETIRED_TYPE_CODES)
    conn.execute(
        sa.text(
            f"UPDATE aircraft_types SET is_active = false, family_id = NULL "
            f"WHERE icao_type_code IN ({retired_list})"
        )
    )

    aircraft_types = sa.table(
        "aircraft_types",
        sa.column("icao_type_code", sa.String),
        sa.column("name", sa.String),
        sa.column("manufacturer", sa.String),
        sa.column("family_id", sa.BigInteger),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        aircraft_types,
        [
            {
                "icao_type_code": code,
                "name": name,
                "manufacturer": manufacturer,
                "family_id": family_ids[family_code],
                "is_active": True,
            }
            for code, name, manufacturer, family_code in NEW_TYPES
        ],
    )

    # Added only now that every row is consistent (reused codes have a
    # family, retired codes are inactive, new codes have a family) -- see
    # 0015's note on why this can't be created before this backfill runs.
    op.create_check_constraint(
        "ck_aircraft_types_active_requires_family",
        "aircraft_types",
        "is_active = false OR family_id IS NOT NULL",
    )


def downgrade() -> None:
    # Dropped first so the restorative updates below (which temporarily
    # leave rows with is_active=true, family_id=NULL) don't violate it.
    op.drop_constraint("ck_aircraft_types_active_requires_family", "aircraft_types")

    new_codes_list = ",".join(f"'{c[0]}'" for c in NEW_TYPES)
    op.execute(f"DELETE FROM aircraft_types WHERE icao_type_code IN ({new_codes_list})")

    retired_list = ",".join(f"'{c}'" for c in RETIRED_TYPE_CODES)
    op.execute(
        f"UPDATE aircraft_types SET is_active = true, family_id = NULL "
        f"WHERE icao_type_code IN ({retired_list})"
    )

    reused_list = ",".join(f"'{c}'" for c in REUSED_TYPE_FAMILY)
    op.execute(f"UPDATE aircraft_types SET family_id = NULL WHERE icao_type_code IN ({reused_list})")

    family_codes_list = ",".join(f"'{c[0]}'" for c in FAMILIES)
    op.execute(f"DELETE FROM aircraft_families WHERE code IN ({family_codes_list})")
