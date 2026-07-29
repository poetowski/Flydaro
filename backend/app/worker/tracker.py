from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aircraft import AircraftRegistry
from app.models.airport import Airport
from app.models.flight import FlightStateSample, TrackedFlight, TrackedFlightStatus
from app.worker import thresholds
from app.worker.geo import haversine_km
from app.worker.opensky_client import StateVector

RESOLVED_STATUSES = (
    TrackedFlightStatus.RESOLVED_LANDED,
    TrackedFlightStatus.RESOLVED_TIMEOUT,
    TrackedFlightStatus.RESOLVED_LOST_SIGNAL,
)


def looks_like_recent_takeoff(state: StateVector, airport: Airport) -> bool:
    if state.on_ground:
        return False
    if state.latitude is None or state.longitude is None:
        return False
    if state.baro_altitude is None or state.baro_altitude > thresholds.TAKEOFF_MAX_ALTITUDE_M:
        return False
    if state.vertical_rate is None or state.vertical_rate < thresholds.TAKEOFF_MIN_VERTICAL_RATE_MS:
        return False
    distance_km = haversine_km(airport.lat, airport.lon, state.latitude, state.longitude)
    return distance_km <= thresholds.TAKEOFF_MAX_DISTANCE_KM


def looks_like_landing(state: StateVector) -> bool:
    if state.on_ground:
        return True
    if state.baro_altitude is None or state.velocity is None or state.vertical_rate is None:
        return False
    return (
        state.baro_altitude <= thresholds.LANDING_MAX_ALTITUDE_M
        and state.velocity <= thresholds.LANDING_MAX_VELOCITY_MS
        and abs(state.vertical_rate) <= thresholds.LANDING_MAX_ABS_VERTICAL_RATE_MS
    )


async def find_open_tracked_flight(db: AsyncSession, icao24: str) -> TrackedFlight | None:
    return await db.scalar(
        select(TrackedFlight).where(
            TrackedFlight.icao24 == icao24,
            TrackedFlight.status.not_in(RESOLVED_STATUSES),
        )
    )


async def resolve_aircraft_type_id(db: AsyncSession, icao24: str) -> int | None:
    """Single PK lookup against our small, curated-types-only registry table
    (populated by worker/aircraft_registry_sync.py). Returns None if this
    icao24 was never matched to one of our curated aircraft types -- that's
    a normal, expected outcome given the free registry's coverage gaps, not
    an error.
    """
    entry = await db.get(AircraftRegistry, icao24.lower())
    return entry.aircraft_type_id if entry else None


async def create_tracked_flight(
    db: AsyncSession, state: StateVector, airport: Airport, observed_at: datetime
) -> TrackedFlight:
    aircraft_type_id = await resolve_aircraft_type_id(db, state.icao24)
    flight = TrackedFlight(
        icao24=state.icao24,
        callsign=state.callsign,
        origin_airport_id=airport.id,
        aircraft_type_id=aircraft_type_id,
        first_seen_at=observed_at,
        first_seen_lat=state.latitude,
        first_seen_lon=state.longitude,
        first_seen_alt=state.baro_altitude,
        first_seen_velocity=state.velocity,
        first_seen_vertical_rate=state.vertical_rate,
        last_seen_at=observed_at,
        last_seen_lat=state.latitude,
        last_seen_lon=state.longitude,
        last_seen_alt=state.baro_altitude,
        last_seen_velocity=state.velocity,
        last_seen_vertical_rate=state.vertical_rate,
        last_seen_on_ground=state.on_ground,
        status=TrackedFlightStatus.AIRBORNE_OPEN,
        capacity_open=True,
    )
    db.add(flight)
    await db.flush()
    return flight


async def record_sample(
    db: AsyncSession, flight: TrackedFlight, state: StateVector, observed_at: datetime
) -> None:
    flight.last_seen_at = observed_at
    flight.last_seen_lat = state.latitude
    flight.last_seen_lon = state.longitude
    flight.last_seen_alt = state.baro_altitude
    flight.last_seen_velocity = state.velocity
    flight.last_seen_vertical_rate = state.vertical_rate
    flight.last_seen_on_ground = state.on_ground

    db.add(
        FlightStateSample(
            tracked_flight_id=flight.id,
            observed_at=observed_at,
            lat=state.latitude,
            lon=state.longitude,
            baro_altitude=state.baro_altitude,
            velocity=state.velocity,
            vertical_rate=state.vertical_rate,
            on_ground=state.on_ground,
            raw={"state": state.raw},
        )
    )
    await db.flush()


def minutes_since(reference: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    return (now - reference).total_seconds() / 60
