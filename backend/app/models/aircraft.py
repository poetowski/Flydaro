from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AircraftType(Base):
    """A specific real aircraft model (e.g. "Airbus A321neo"), resolved from
    OpenSky's registry by aircraft_registry_sync.py and used to display a
    flight's precise model. Licensing itself lives one level up, on
    AircraftFamily -- family_id is nullable only for retired types (is_active
    false), which no license covers anymore.
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


class AircraftRegistry(Base):
    """Bulk reference data resolved from OpenSky's free aircraft metadata CSV,
    refreshed periodically by worker/aircraft_registry_sync.py -- never
    queried live per-request. Only holds icao24s that matched one of our
    curated aircraft_types, so this table stays small relative to OpenSky's
    full (~600k row) database.
    """

    __tablename__ = "aircraft_registry"

    icao24: Mapped[str] = mapped_column(String(6), primary_key=True)
    aircraft_type_id: Mapped[int] = mapped_column(
        ForeignKey("aircraft_types.id"), nullable=False, index=True
    )
    registration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
