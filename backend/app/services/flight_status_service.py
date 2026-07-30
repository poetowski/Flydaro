"""On-demand landing confirmation: the actual gate for settling a rental's
reward, triggered when a player checks their rentals rather than on a fixed
poll schedule. There is no background poller -- this (and
flight_discovery_service.py's per-airport sweep) is the only path a flight
ever resolves through. Tries a live single-aircraft OpenSky state first,
falls back to OpenSky's own historical arrival record, and only then falls
back further to the time-based duration/lost-signal ceilings -- landing
confirmation (live or historical) always wins over a ceiling fallback if
both would apply, since it reflects the true outcome.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.airport import Airport
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.services import rental_service, settlement_service
from app.worker import thresholds, tracker
from app.worker.opensky_client import OpenSkyClient

logger = logging.getLogger(__name__)


def _find_matching_leg(legs: list[dict], origin_icao4: str, first_seen_at: datetime) -> dict | None:
    first_seen_ts = first_seen_at.timestamp()
    tolerance_seconds = thresholds.HISTORICAL_LEG_MATCH_TOLERANCE_MINUTES * 60

    candidates = [
        leg
        for leg in legs
        if leg.get("firstSeen") is not None
        and abs(leg["firstSeen"] - first_seen_ts) <= tolerance_seconds
    ]
    if not candidates:
        return None

    same_airport = [leg for leg in candidates if leg.get("estDepartureAirport") == origin_icao4]
    pool = same_airport or candidates
    return min(pool, key=lambda leg: abs(leg["firstSeen"] - first_seen_ts))


async def refresh_flight_status(
    db: AsyncSession, client: OpenSkyClient, flight: TrackedFlight, airport: Airport
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
    # of ADS-B coverage right now. Ask OpenSky's own historical record
    # rather than guessing from silence alone.
    begin = int(flight.first_seen_at.timestamp()) - 300
    end = int(now.timestamp())
    legs = await client.get_aircraft_flights(flight.icao24, begin, end)
    matching_leg = _find_matching_leg(legs, airport.icao4, flight.first_seen_at)

    if matching_leg is not None and matching_leg.get("estArrivalAirport"):
        resolved_at = datetime.fromtimestamp(matching_leg["lastSeen"], tz=timezone.utc)
        logger.info("Flight %s confirmed landed via OpenSky historical record", flight.icao24)
        await rental_service.resolve_tracked_flight(
            db,
            flight,
            TrackedFlightStatus.RESOLVED_LANDED,
            settlement_service.LANDED_REASON,
            {
                "confirmed_via": "historical_flights_endpoint",
                "est_arrival_airport": matching_leg["estArrivalAirport"],
                "duration_minutes": round(tracker.minutes_since(flight.first_seen_at, resolved_at), 1),
            },
            resolved_at=resolved_at,
        )
        await db.flush()
        return flight

    # Neither live nor historical data confirms a landing -- only now fall
    # back to the time-based ceilings (duration first, then lost signal),
    # scoped to this one flight rather than a global sweep.
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
