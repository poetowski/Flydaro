"""On-demand landing confirmation: the actual gate for settling a rental's
reward, triggered when a player checks their rentals rather than on a fixed
poll schedule. The background poller's live on_ground/altitude heuristic
(see worker/resolver.py) is a best-effort fast path that only works while
it's actually running continuously -- this is the reliable fallback that
works even if the app was asleep through the real landing, by asking
OpenSky directly (live single-aircraft state, or its own historical
arrival record) whether the flight is actually down.
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
        else:
            # Still airborne -- record it like a normal sample so
            # last_seen_*/duration stay accurate for later checks.
            await tracker.record_sample(db, flight, state, now)
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
