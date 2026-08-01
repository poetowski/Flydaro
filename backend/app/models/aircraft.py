from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AircraftType(Base):
    """A specific real aircraft model (e.g. "Airbus A321neo"), resolved
    directly from each live adsb.fi position report (its inline ICAO type
    code, see app.worker.tracker.resolve_aircraft_type_id_by_code) and used
    to display a flight's precise model. Licensing itself lives one level
    up, on AircraftFamily -- family_id is nullable only for retired types
    (is_active false), which no license covers anymore.
    """

    __tablename__ = "aircraft_types"
    __table_args__ = (
        CheckConstraint(
            "is_active = false OR family_id IS NOT NULL",
            name="ck_aircraft_types_active_requires_family",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    icao_type_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    family_id: Mapped[int | None] = mapped_column(
        ForeignKey("aircraft_families.id"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
