from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_opensky_client
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.airport import Airport
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.models.user import User
from app.schemas.flight import TrackedFlightOut
from app.services import flight_discovery_service, license_service
from app.worker.opensky_client import OpenSkyClient

router = APIRouter(prefix="/flights", tags=["flights"])

OPEN_BOARD_STATUSES = (
    TrackedFlightStatus.AIRBORNE_OPEN,
    TrackedFlightStatus.AIRBORNE_LOCKED,
    TrackedFlightStatus.LANDING_SUSPECTED,
)


@router.get("/board", response_model=list[TrackedFlightOut])
async def get_flight_board(
    airport_id: int | None = None,
    aircraft_type_id: int | None = None,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: OpenSkyClient = Depends(get_opensky_client),
) -> list[TrackedFlight]:
    unlocked_airport_ids = await license_service.get_unlocked_airport_ids(db, current_user.id)
    unlocked_type_ids = await license_service.get_unlocked_aircraft_type_ids(db, current_user.id)

    # Ad-hoc discovery: no background poller exists, so this request itself
    # is what looks for new flights and advances/resolves existing ones at
    # the airports actually in scope, before the DB query below reads back
    # the (now possibly updated) result set.
    scope_airport_ids = unlocked_airport_ids if airport_id is None else (unlocked_airport_ids & {airport_id})
    if scope_airport_ids:
        airports = list(await db.scalars(select(Airport).where(Airport.id.in_(scope_airport_ids))))
        await flight_discovery_service.refresh_board_for_airports(db, client, airports)
        await db.commit()

    # Floor, not just a UI convenience: applied unconditionally, regardless
    # of whether airport_id/aircraft_type_id narrow further below, so a user
    # can never see another airport's or a locked aircraft type's flights
    # just by omitting/varying the params.
    stmt = select(TrackedFlight).where(
        TrackedFlight.origin_airport_id.in_(unlocked_airport_ids),
        TrackedFlight.aircraft_type_id.in_(unlocked_type_ids),
        # Hides flights whose aircraft type couldn't be resolved at all --
        # a query-level filter, not just a betting-time check.
        TrackedFlight.aircraft_type_id.is_not(None),
    )
    if status_filter is not None:
        try:
            stmt = stmt.where(TrackedFlight.status == TrackedFlightStatus(status_filter))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter"
            ) from exc
    else:
        stmt = stmt.where(TrackedFlight.status.in_(OPEN_BOARD_STATUSES))
    if airport_id is not None:
        stmt = stmt.where(TrackedFlight.origin_airport_id == airport_id)
    if aircraft_type_id is not None:
        # Composes on top of the unconditional floor above, same pattern as airport_id.
        stmt = stmt.where(TrackedFlight.aircraft_type_id == aircraft_type_id)
    stmt = stmt.order_by(TrackedFlight.first_seen_at.desc())

    result = await db.scalars(stmt)
    return list(result.all())


@router.get("/{flight_id}", response_model=TrackedFlightOut)
async def get_flight(
    flight_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedFlight:
    flight = await db.get(TrackedFlight, flight_id)
    if flight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flight not found")
    return flight
