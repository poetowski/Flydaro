import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_adsb_client
from app.core.security import get_current_user
from app.db.session import DirectSessionLocal, get_db
from app.models.airport import Airport
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.models.user import User
from app.schemas.flight import TrackedFlightOut
from app.services import flight_discovery_service, license_service
from app.worker.adsb_client import AdsbClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flights", tags=["flights"])

OPEN_BOARD_STATUSES = (
    TrackedFlightStatus.AIRBORNE_OPEN,
    TrackedFlightStatus.AIRBORNE_LOCKED,
    TrackedFlightStatus.LANDING_SUSPECTED,
)


async def _refresh_board_background(airport_ids: set[int], client: AdsbClient) -> None:
    """Runs after the response is already sent -- needs its own DB session
    (the request's is closed by the time background tasks run), but shares
    the same singleton AdsbClient so its 1 req/sec rate-limit gate still
    applies globally, exactly as it does for every other caller."""
    try:
        async with DirectSessionLocal() as bg_db:
            airports = list(await bg_db.scalars(select(Airport).where(Airport.id.in_(airport_ids))))
            await flight_discovery_service.refresh_board_for_airports(bg_db, client, airports)
            await bg_db.commit()
    except Exception:
        logger.exception("Background board discovery failed")


@router.get("/board", response_model=list[TrackedFlightOut])
async def get_flight_board(
    background_tasks: BackgroundTasks,
    airport_id: int | None = None,
    aircraft_family_id: int | None = None,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    client: AdsbClient = Depends(get_adsb_client),
) -> list[TrackedFlight]:
    unlocked_airport_ids = await license_service.get_unlocked_airport_ids(db, current_user.id)
    unlocked_type_ids = await license_service.get_unlocked_aircraft_type_ids(db, current_user.id)

    # Ad-hoc discovery: no background poller exists, so something has to
    # look for new flights and advance/resolve existing ones at the
    # airports actually in scope. Deferred to a background task (runs after
    # the response is sent) rather than awaited here -- the response reads
    # whatever's already committed, so page loads never block on adsb.fi's
    # ~1 req/sec rate limit. refresh_board_for_airports itself already
    # no-ops for any airport whose last_polled_at isn't stale yet, so
    # scheduling this unconditionally is cheap and correct.
    scope_airport_ids = unlocked_airport_ids if airport_id is None else (unlocked_airport_ids & {airport_id})
    if scope_airport_ids:
        background_tasks.add_task(_refresh_board_background, scope_airport_ids, client)

    # Floor, not just a UI convenience: applied unconditionally, regardless
    # of whether airport_id/aircraft_family_id narrow further below, so a
    # user can never see another airport's or a locked aircraft family's
    # flights just by omitting/varying the params.
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
    if aircraft_family_id is not None:
        # Filters across every member type of the family at once (e.g.
        # selecting "Airbus A320 Family" surfaces A319/A320/A321/neo flights
        # together) -- composes on top of the unconditional floor above,
        # same pattern as airport_id.
        family_type_ids = await license_service.expand_family_to_type_ids(db, aircraft_family_id)
        stmt = stmt.where(TrackedFlight.aircraft_type_id.in_(family_type_ids))
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
