import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, Enum, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# JSONB on Postgres (production/Neon), plain JSON elsewhere (SQLite in tests).
JsonVariant = JSON().with_variant(JSONB(), "postgresql")


class TrackedFlightStatus(str, enum.Enum):
    AIRBORNE_OPEN = "AIRBORNE_OPEN"
    AIRBORNE_LOCKED = "AIRBORNE_LOCKED"
    LANDING_SUSPECTED = "LANDING_SUSPECTED"
    RESOLVED_LANDED = "RESOLVED_LANDED"
    RESOLVED_TIMEOUT = "RESOLVED_TIMEOUT"
    RESOLVED_LOST_SIGNAL = "RESOLVED_LOST_SIGNAL"

    @property
    def is_resolved(self) -> bool:
        return self in (
            TrackedFlightStatus.RESOLVED_LANDED,
            TrackedFlightStatus.RESOLVED_TIMEOUT,
            TrackedFlightStatus.RESOLVED_LOST_SIGNAL,
        )


class TrackedFlight(Base):
    __tablename__ = "tracked_flights"
    __table_args__ = (
        # Only one *open* (non-resolved) tracked flight per aircraft at a time.
        Index(
            "ix_tracked_flights_open_icao24",
            "icao24",
            unique=True,
            postgresql_where=(
                "status not in ('RESOLVED_LANDED', 'RESOLVED_TIMEOUT', 'RESOLVED_LOST_SIGNAL')"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    icao24: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    callsign: Mapped[str | None] = mapped_column(String(20), nullable=True)
    origin_airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), nullable=False)
    # NULL = unresolved (icao24 not in the free aircraft registry, or its type
    # isn't one of our curated ones) -- both the board's hide-signal and the
    # bet-placement gate's "unknown type" rejection key off this being NULL.
    aircraft_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("aircraft_types.id"), nullable=True, index=True
    )

    first_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    first_seen_lat: Mapped[float] = mapped_column(Float, nullable=False)
    first_seen_lon: Mapped[float] = mapped_column(Float, nullable=False)
    first_seen_alt: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_seen_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_seen_vertical_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    last_seen_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_alt: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_vertical_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_on_ground: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    status: Mapped[TrackedFlightStatus] = mapped_column(
        Enum(TrackedFlightStatus, name="tracked_flight_status", native_enum=False),
        nullable=False,
        default=TrackedFlightStatus.AIRBORNE_OPEN,
    )
    capacity_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Set the first time on_ground/low-speed criteria are met; used to time the
    # landing-confirmation grace period independent of poll cadence.
    landing_suspected_at: Mapped[datetime | None] = mapped_column(nullable=True)

    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolution_summary: Mapped[dict | None] = mapped_column(JsonVariant, nullable=True)

    # Throttle for the on-demand OpenSky confirmation check (see
    # app/services/flight_status_service.py) -- a user hammering refresh on
    # /rentals/mine must not turn into an OpenSky call per click.
    last_status_check_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class FlightStateSample(Base):
    __tablename__ = "flight_state_samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracked_flight_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_flights.id"), nullable=False, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    baro_altitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    vertical_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_ground: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    raw: Mapped[dict | None] = mapped_column(JsonVariant, nullable=True)
