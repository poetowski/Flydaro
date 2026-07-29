from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.models.user import User
from app.schemas.flight import TrackedFlightOut

router = APIRouter(prefix="/flights", tags=["flights"])

OPEN_BOARD_STATUSES = (
    TrackedFlightStatus.AIRBORNE_OPEN,
    TrackedFlightStatus.AIRBORNE_LOCKED,
    TrackedFlightStatus.LANDING_SUSPECTED,
)


@router.get("/board", response_model=list[TrackedFlightOut])
async def get_flight_board(
    airport_id: int | None = None,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TrackedFlight]:
    stmt = select(TrackedFlight)
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
