from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import get_current_admin_user
from app.db.session import get_db
from app.models.aircraft import AircraftType
from app.models.airport import Airport
from app.models.flight import TrackedFlight
from app.models.poller_heartbeat import PollerHeartbeat
from app.models.user import User
from app.schemas.admin import (
    ActiveAirportOut,
    FlightStatusCountOut,
    PollerHealthOut,
    PollerHeartbeatOut,
    RecentFlightOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

RECENT_FLIGHTS_LIMIT = 10


@router.get("/poller-health", response_model=PollerHealthOut)
async def get_poller_health(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> PollerHealthOut:
    heartbeat = await db.get(PollerHeartbeat, 1)
    now = datetime.now(timezone.utc)
    seconds_since_last_tick = (
        (now - heartbeat.last_tick_at).total_seconds()
        if heartbeat is not None and heartbeat.last_tick_at is not None
        else None
    )
    heartbeat_out = PollerHeartbeatOut(
        last_tick_at=heartbeat.last_tick_at if heartbeat else None,
        last_success_at=heartbeat.last_success_at if heartbeat else None,
        last_error=heartbeat.last_error if heartbeat else None,
        credits_remaining=heartbeat.credits_remaining if heartbeat else None,
        last_opensky_status=heartbeat.last_opensky_status if heartbeat else None,
        last_opensky_detail=heartbeat.last_opensky_detail if heartbeat else None,
        seconds_since_last_tick=seconds_since_last_tick,
        expected_interval_seconds=settings.poller_interval_seconds,
    )

    status_rows = await db.execute(
        select(TrackedFlight.status, func.count(TrackedFlight.id)).group_by(TrackedFlight.status)
    )
    status_counts = [
        FlightStatusCountOut(status=status_value.value, count=count)
        for status_value, count in status_rows
    ]

    recent_rows = await db.execute(
        select(
            TrackedFlight.id,
            TrackedFlight.icao24,
            TrackedFlight.callsign,
            Airport.name.label("airport_name"),
            AircraftType.name.label("aircraft_type_name"),
            TrackedFlight.status,
            TrackedFlight.first_seen_at,
        )
        .join(Airport, TrackedFlight.origin_airport_id == Airport.id)
        .outerjoin(AircraftType, TrackedFlight.aircraft_type_id == AircraftType.id)
        .order_by(TrackedFlight.created_at.desc())
        .limit(RECENT_FLIGHTS_LIMIT)
    )
    recent_flights = [
        RecentFlightOut(
            id=row.id,
            icao24=row.icao24,
            callsign=row.callsign,
            origin_airport_name=row.airport_name,
            aircraft_type_name=row.aircraft_type_name,
            status=row.status.value,
            first_seen_at=row.first_seen_at,
        )
        for row in recent_rows
    ]

    active_airports = list(
        await db.scalars(select(Airport).where(Airport.is_active.is_(True)).order_by(Airport.icao4))
    )
    active_airports_out = [ActiveAirportOut.model_validate(a) for a in active_airports]

    return PollerHealthOut(
        heartbeat=heartbeat_out,
        status_counts=status_counts,
        recent_flights=recent_flights,
        active_airports=active_airports_out,
    )
