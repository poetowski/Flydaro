from datetime import datetime

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[int] = mapped_column(primary_key=True)
    icao4: Mapped[str] = mapped_column(String(4), unique=True, nullable=False, index=True)
    iata: Mapped[str | None] = mapped_column(String(3), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_lamin: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_lomin: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_lamax: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_lomax: Mapped[float] = mapped_column(Float, nullable=False)
    is_starter: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Historical unlock-scoping flag ("has any player unlocked this airport
    # yet"), flipped True by license_service.unlock_airport(). No longer
    # drives a background scheduler (there is none) -- nothing currently
    # gates on this column, it's informational only. Per-user access is
    # is_starter OR a row in user_airport_unlocks; see
    # app/services/license_service.py.
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    unlock_cost_credits: Mapped[int] = mapped_column(nullable=False, default=0)
    # Throttle for ad-hoc board discovery (app/services/flight_discovery_service.py)
    # -- avoids N concurrent users loading the board for this airport each
    # triggering a fresh OpenSky bbox call.
    last_polled_at: Mapped[datetime | None] = mapped_column(nullable=True)
