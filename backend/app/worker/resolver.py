import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.services import rental_service, settlement_service
from app.worker import thresholds
from app.worker.tracker import RESOLVED_STATUSES, minutes_since

logger = logging.getLogger(__name__)


def _summary(flight: TrackedFlight, duration_minutes: float) -> dict:
    return {
        "duration_minutes": round(duration_minutes, 1),
        "last_lat": flight.last_seen_lat,
        "last_lon": flight.last_seen_lon,
        "last_alt": flight.last_seen_alt,
        "origin_airport_id": flight.origin_airport_id,
    }


async def resolve_pending_landings(db: AsyncSession) -> None:
    """Confirm LANDING_SUSPECTED flights whose grace period has elapsed."""
    now = datetime.now(timezone.utc)
    flights = await db.scalars(
        select(TrackedFlight).where(TrackedFlight.status == TrackedFlightStatus.LANDING_SUSPECTED)
    )
    for flight in flights:
        if flight.landing_suspected_at is None:
            continue
        if minutes_since(flight.landing_suspected_at, now) < thresholds.LANDING_GRACE_PERIOD_MINUTES:
            continue

        duration_minutes = minutes_since(flight.first_seen_at, now)
        logger.info("Flight %s confirmed landed after grace period", flight.icao24)
        await rental_service.resolve_tracked_flight(
            db,
            flight,
            TrackedFlightStatus.RESOLVED_LANDED,
            settlement_service.LANDED_REASON,
            _summary(flight, duration_minutes),
            resolved_at=now,
        )
    await db.commit()


async def sweep_timeouts_and_lost_signal(db: AsyncSession) -> None:
    """Runs every tick regardless of this tick's poll results, so an aircraft
    that simply vanishes from ADS-B coverage still resolves on schedule.
    """
    now = datetime.now(timezone.utc)
    flights = await db.scalars(
        select(TrackedFlight).where(TrackedFlight.status.not_in(RESOLVED_STATUSES))
    )
    for flight in flights:
        duration_minutes = minutes_since(flight.first_seen_at, now)
        if duration_minutes > thresholds.MAX_FLIGHT_DURATION_CEILING_MINUTES:
            logger.info("Flight %s hit max duration ceiling, resolving via timeout", flight.icao24)
            await rental_service.resolve_tracked_flight(
                db,
                flight,
                TrackedFlightStatus.RESOLVED_TIMEOUT,
                settlement_service.TIMEOUT_REASON,
                _summary(flight, duration_minutes),
                resolved_at=now,
            )
            continue

        silence_minutes = minutes_since(flight.last_seen_at, now)
        if silence_minutes > thresholds.LOST_SIGNAL_CEILING_MINUTES:
            logger.info("Flight %s lost signal, resolving via fallback", flight.icao24)
            await rental_service.resolve_tracked_flight(
                db,
                flight,
                TrackedFlightStatus.RESOLVED_LOST_SIGNAL,
                settlement_service.LOST_SIGNAL_REASON,
                _summary(flight, duration_minutes),
                resolved_at=now,
            )
    await db.commit()
