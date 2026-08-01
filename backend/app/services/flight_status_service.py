"""On-demand landing confirmation: the actual gate for settling a rental's
reward, triggered when a player checks their rentals rather than on a fixed
poll schedule. There is no background poller -- this (and
flight_discovery_service.py's per-airport sweep) is the only path a flight
ever resolves through. Tries a live single-aircraft adsb.fi state first, and
only then falls back to the time-based duration/lost-signal ceilings --
landing confirmation always wins over a ceiling fallback if both would
apply, since it reflects the true outcome.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.airport import Airport
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.services import rental_service, settlement_service
from app.worker import thresholds, tracker
from app.worker.adsb_client import AdsbClient

logger = logging.getLogger(__name__)


async def refresh_flight_status(
    db: AsyncSession, client: AdsbClient, flight: TrackedFlight, airport: Airport
) -> TrackedFlight:
    """Idempotent: safe to call on every rental fetch. No-ops immediately if
    the flight is already resolved, or if it was explicitly checked too
    recently (STATUS_CHECK_MIN_INTERVAL_SECONDS)."""
    if flight.status.is_resolved:
        return flight

    now = datetime.now(timezone.utc)
    if (
        flight.last_status_check_at is not None
        and (now - flight.last_status_check_at) < timedelta(seconds=thresholds.STATUS_CHECK_MIN_INTERVAL_SECONDS)
    ):
        return flight
    flight.last_status_check_at = now

    state = await client.get_state_for_icao24(flight.icao24)
    if state is not None:
        if state.on_ground:
            logger.info("Flight %s confirmed landed via live on-demand check", flight.icao24)
            await rental_service.resolve_tracked_flight(
                db,
                flight,
                TrackedFlightStatus.RESOLVED_LANDED,
                settlement_service.LANDED_REASON,
                {"confirmed_via": "live_state", "on_ground": True},
                resolved_at=now,
            )
            await db.flush()
            return flight

        # Still airborne -- record it like a normal sample so
        # last_seen_*/duration stay accurate for later checks. A fresh live
        # sample rules out lost-signal, but not an outlier long-haul flight
        # against the absolute duration ceiling.
        await tracker.record_sample(db, flight, state, now)
        if tracker.duration_ceiling_breached(flight, now):
            duration = tracker.minutes_since(flight.first_seen_at, now)
            await rental_service.resolve_tracked_flight(
                db,
                flight,
                TrackedFlightStatus.RESOLVED_TIMEOUT,
                settlement_service.TIMEOUT_REASON,
                tracker.build_resolution_summary(flight, duration),
                resolved_at=now,
            )
        await db.flush()
        return flight

    # No live report at all: could mean landed and gone quiet, or just out
    # of ADS-B coverage right now -- adsb.fi (unlike OpenSky) has no
    # historical-lookup endpoint to disambiguate further, so fall straight
    # to the time-based ceilings (duration first, then lost signal), scoped
    # to this one flight rather than a global sweep.
    if tracker.duration_ceiling_breached(flight, now):
        duration = tracker.minutes_since(flight.first_seen_at, now)
        await rental_service.resolve_tracked_flight(
            db,
            flight,
            TrackedFlightStatus.RESOLVED_TIMEOUT,
            settlement_service.TIMEOUT_REASON,
            tracker.build_resolution_summary(flight, duration),
            resolved_at=now,
        )
    elif tracker.lost_signal_ceiling_breached(flight, now):
        duration = tracker.minutes_since(flight.first_seen_at, now)
        await rental_service.resolve_tracked_flight(
            db,
            flight,
            TrackedFlightStatus.RESOLVED_LOST_SIGNAL,
            settlement_service.LOST_SIGNAL_REASON,
            tracker.build_resolution_summary(flight, duration),
            resolved_at=now,
        )

    await db.flush()
    return flight
