"""Ad-hoc flight discovery: called from GET /flights/board on every request
(throttled per-airport), not from a background loop. Discovers new takeoffs,
keeps existing tracked flights' samples fresh, closes the capacity window
after CAPACITY_WINDOW_MINUTES, and advances/confirms landing-suspicion for
flights at the airports actually being queried right now. Also applies the
time-based duration/lost-signal/grace-period ceiling fallbacks to every
non-resolved flight at those airports (not just ones with a fresh sample
this call), so a flight nobody currently holds a rental on still eventually
resolves instead of sitting open forever with no background sweep to catch
it.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.airport import Airport
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.services import rental_service, settlement_service
from app.worker import thresholds, tracker
from app.worker.adsb_client import AdsbClient, StateVector

logger = logging.getLogger(__name__)


async def _resolve_via_ceiling_or_grace(db: AsyncSession, flight: TrackedFlight, now: datetime) -> None:
    if flight.status == TrackedFlightStatus.LANDING_SUSPECTED and tracker.landing_grace_period_elapsed(
        flight, now
    ):
        duration = tracker.minutes_since(flight.first_seen_at, now)
        logger.info("Flight %s confirmed landed after grace period", flight.icao24)
        await rental_service.resolve_tracked_flight(
            db,
            flight,
            TrackedFlightStatus.RESOLVED_LANDED,
            settlement_service.LANDED_REASON,
            tracker.build_resolution_summary(flight, duration),
            resolved_at=now,
        )
        return

    if tracker.duration_ceiling_breached(flight, now):
        duration = tracker.minutes_since(flight.first_seen_at, now)
        logger.info("Flight %s hit max duration ceiling, resolving via timeout", flight.icao24)
        await rental_service.resolve_tracked_flight(
            db,
            flight,
            TrackedFlightStatus.RESOLVED_TIMEOUT,
            settlement_service.TIMEOUT_REASON,
            tracker.build_resolution_summary(flight, duration),
            resolved_at=now,
        )
        return

    if tracker.lost_signal_ceiling_breached(flight, now):
        duration = tracker.minutes_since(flight.first_seen_at, now)
        logger.info("Flight %s lost signal, resolving via fallback", flight.icao24)
        await rental_service.resolve_tracked_flight(
            db,
            flight,
            TrackedFlightStatus.RESOLVED_LOST_SIGNAL,
            settlement_service.LOST_SIGNAL_REASON,
            tracker.build_resolution_summary(flight, duration),
            resolved_at=now,
        )


async def _process_airport_states(
    db: AsyncSession, airport: Airport, states: list[StateVector], now: datetime
) -> None:
    state_by_icao24 = {s.icao24: s for s in states if s.icao24}

    for icao24, state in state_by_icao24.items():
        flight = await tracker.find_open_tracked_flight(db, icao24)
        if flight is None:
            if tracker.looks_like_recent_takeoff(state, airport):
                logger.info("New tracked flight %s near %s (ad-hoc discovery)", icao24, airport.icao4)
                await tracker.create_tracked_flight(db, state, airport, now)
            continue
        if flight.origin_airport_id != airport.id:
            continue  # tracked under a different airport already -- leave alone

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
            await rental_service.rollback_landing_suspected(db, flight)

    # Time-based sweep over every non-resolved flight at this airport,
    # independent of whether this call's query returned fresh data for it --
    # a flight that stopped transmitting must still resolve eventually.
    open_flights = list(
        await db.scalars(
            select(TrackedFlight).where(
                TrackedFlight.origin_airport_id == airport.id,
                TrackedFlight.status.not_in(tracker.RESOLVED_STATUSES),
            )
        )
    )
    for flight in open_flights:
        await _resolve_via_ceiling_or_grace(db, flight, now)


async def refresh_board_for_airports(
    db: AsyncSession, client: AdsbClient, airports: list[Airport]
) -> None:
    """Entry point called from GET /flights/board. Only airports whose
    last_polled_at is stale (or unset) actually make an adsb.fi call this
    request; still fanned out via asyncio.gather so per-request latency
    doesn't scale linearly with the number of unlocked airports -- the
    client itself (not this concurrency) is what keeps every call, however
    it's issued, paced to adsb.fi's global 1 req/sec ceiling.
    """
    now = datetime.now(timezone.utc)
    due = [
        a
        for a in airports
        if a.last_polled_at is None
        or (now - a.last_polled_at) >= timedelta(seconds=thresholds.AIRPORT_POLL_MIN_INTERVAL_SECONDS)
    ]
    if not due:
        return

    results = await asyncio.gather(
        *(
            client.get_states_near(a.lat, a.lon, thresholds.AIRPORT_QUERY_RADIUS_NM)
            for a in due
        ),
        return_exceptions=True,
    )

    for airport, states_or_exc in zip(due, results):
        airport.last_polled_at = now
        if isinstance(states_or_exc, BaseException):
            logger.exception("Discovery query failed for %s", airport.icao4, exc_info=states_or_exc)
            continue
        await _process_airport_states(db, airport, states_or_exc, now)

    await db.flush()
