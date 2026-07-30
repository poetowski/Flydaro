"""widen airport bounding boxes to match the extended takeoff-detection window

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-30

"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

# Was 0.35 (see 0002/0004). Raising TAKEOFF_MAX_DISTANCE_KM to 50km (from
# 15km, see thresholds.py) means the OpenSky bbox query itself must stay
# wide enough to still contain an aircraft that far out, or it drops off
# OpenSky's response before the new distance ceiling is ever reached. At
# the highest-latitude seeded airport (EKCH Copenhagen, 55.618N), 1 degree
# of longitude is ~62.7km, so 1.0 degree margin (~62.7km longitude, ~111km
# latitude there) comfortably covers 50km in both directions; margin is a
# flat degree value applied to every airport regardless of latitude, so it
# under-covers longitude more the further from the equator a future airport
# might be added -- fine for all airports seeded today, worth revisiting
# with a latitude-aware formula if that changes.
OLD_MARGIN = 0.35
NEW_MARGIN = 1.0


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE airports SET
            bbox_lamin = lat - {NEW_MARGIN},
            bbox_lomin = lon - {NEW_MARGIN},
            bbox_lamax = lat + {NEW_MARGIN},
            bbox_lomax = lon + {NEW_MARGIN}
        """
    )


def downgrade() -> None:
    op.execute(
        f"""
        UPDATE airports SET
            bbox_lamin = lat - {OLD_MARGIN},
            bbox_lomin = lon - {OLD_MARGIN},
            bbox_lamax = lat + {OLD_MARGIN},
            bbox_lomax = lon + {OLD_MARGIN}
        """
    )
