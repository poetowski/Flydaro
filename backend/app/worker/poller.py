import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import DirectSessionLocal
from app.models.airport import Airport
from app.models.flight import TrackedFlightStatus
from app.services import rental_service
from app.worker import heartbeat, resolver, thresholds, tracker
from app.worker.opensky_client import OpenSkyClient

logger = logging.getLogger(__name__)


async def _process_airport(db: AsyncSession, client: OpenSkyClient, airport: Airport, now: datetime) -> None:
    states = await client.get_states_in_bbox(
        airport.bbox_lamin, airport.bbox_lomin, airport.bbox_lamax, airport.bbox_lomax
    )
    for state in states:
        if not state.icao24:
            continue

        flight = await tracker.find_open_tracked_flight(db, state.icao24)

        if flight is None:
            if tracker.looks_like_recent_takeoff(state, airport):
                flight = await tracker.create_tracked_flight(db, state, airport, now)
                logger.info(
                    "New tracked flight %s (%s) near %s", state.icao24, state.callsign, airport.icao4
                )
            continue

        await tracker.record_sample(db, flight, state, now)

        if (
            flight.status == TrackedFlightStatus.AIRBORNE_OPEN
            and tracker.minutes_since(flight.first_seen_at, now) >= thresholds.CAPACITY_WINDOW_MINUTES
        ):
            await rental_service.lock_capacity(db, flight)

        elif flight.status == TrackedFlightStatus.AIRBORNE_LOCKED and tracker.looks_like_landing(state):
            await rental_service.mark_landing_suspected(db, flight, now)

        elif flight.status == TrackedFlightStatus.LANDING_SUSPECTED and not tracker.looks_like_landing(
            state
        ):
            # Re-accelerated/climbing again: touch-and-go or go-around, not a real landing.
            await rental_service.rollback_landing_suspected(db, flight)


async def run_tick(db: AsyncSession, client: OpenSkyClient) -> None:
    now = datetime.now(timezone.utc)
    airports = list(await db.scalars(select(Airport).where(Airport.is_active.is_(True))))
    for airport in airports:
        try:
            # Savepoint per airport: a failure processing one airport (e.g. a
            # bad OpenSky response) only unwinds that airport's changes, not
            # the whole tick's progress on every other airport.
            async with db.begin_nested():
                await _process_airport(db, client, airport, now)
        except Exception:
            logger.exception("Error processing airport %s", airport.icao4)
    await db.commit()

    # Independent of this tick's poll results, so vanished aircraft still
    # resolve on schedule even if they never reappear.
    await resolver.resolve_pending_landings(db)
    await resolver.sweep_timeouts_and_lost_signal(db)


async def run_forever(client: OpenSkyClient, interval_seconds: int) -> None:
    """Poll on an interval until cancelled. Shared by the standalone worker
    process and, on deployments without a separate worker service, an
    in-process background task started from the API's lifespan."""
    while True:
        now = datetime.now(timezone.utc)
        error_message: str | None = None
        try:
            async with DirectSessionLocal() as db:
                await run_tick(db, client)
        except Exception as exc:
            logger.exception("Poller tick failed")
            error_message = str(exc) or exc.__class__.__name__

        # Deliberately a SEPARATE session/transaction from run_tick's `db`
        # above. If run_tick failed because ITS session/connection is
        # broken (e.g. a Neon connectivity blip mid-transaction), that
        # session is left needing a rollback before reuse -- a brand new
        # DirectSessionLocal() sidesteps that entirely.
        try:
            async with DirectSessionLocal() as heartbeat_db:
                await heartbeat.record_tick(
                    heartbeat_db,
                    now=now,
                    success=error_message is None,
                    error=error_message,
                    credits_remaining=client.credits_remaining,
                    opensky_status=client.last_status_code,
                    opensky_detail=client.last_status_detail,
                )
                await heartbeat_db.commit()
        except Exception:
            # A heartbeat-write failure must never take down the poll loop.
            logger.exception("Failed to record poller heartbeat")

        await asyncio.sleep(interval_seconds)
