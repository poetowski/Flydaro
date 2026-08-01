"""add rentals.display_code -- human-readable rental name

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-01

"""
import random
import string

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

# Matches app/services/rental_service.py's generate_display_code exactly --
# keep both in sync if either changes.
ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "O0I1")
SUFFIX_LENGTH = 5


def _generate_code(departure_at, used: set[str]) -> str:
    for _ in range(20):
        suffix = "".join(random.choices(ALPHABET, k=SUFFIX_LENGTH))
        code = f"{departure_at.strftime('%Y%m%d-%H%M')}-{suffix}"
        if code not in used:
            used.add(code)
            return code
    raise RuntimeError("Could not generate a unique rental display_code during backfill")


def upgrade() -> None:
    op.add_column("rentals", sa.Column("display_code", sa.String(30), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT r.id, tf.first_seen_at
            FROM rentals r
            JOIN tracked_flights tf ON tf.id = r.tracked_flight_id
            """
        )
    ).fetchall()

    used: set[str] = set()
    for rental_id, first_seen_at in rows:
        code = _generate_code(first_seen_at, used)
        bind.execute(
            sa.text("UPDATE rentals SET display_code = :code WHERE id = :id"),
            {"code": code, "id": rental_id},
        )

    op.alter_column("rentals", "display_code", nullable=False)
    op.create_index("ix_rentals_display_code", "rentals", ["display_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_rentals_display_code", table_name="rentals")
    op.drop_column("rentals", "display_code")
