from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from app.db.base import Base


class AircraftFamily(Base):
    """The unit of aircraft licensing -- one purchasable license covers every
    AircraftType row whose family_id points here (e.g. "Airbus A320 Family"
    covers A318/A319/A320/A321 and their neo variants). AircraftType itself
    stays a granular per-real-model reference table, used for display and
    for tracker.py's exact-typecode matching (see resolve_aircraft_type_id_by_code),
    not licensing.
    """

    __tablename__ = "aircraft_families"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_starter: Mapped[bool] = mapped_column(default=False, nullable=False)
    unlock_cost_credits: Mapped[int] = mapped_column(nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
