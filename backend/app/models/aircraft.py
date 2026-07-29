from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AircraftType(Base):
    __tablename__ = "aircraft_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    icao_type_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    is_starter: Mapped[bool] = mapped_column(default=False, nullable=False)
    unlock_cost_credits: Mapped[int] = mapped_column(nullable=False, default=0)
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
