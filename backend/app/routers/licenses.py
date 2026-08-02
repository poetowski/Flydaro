from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_detail import error_detail
from app.core.exceptions import ConflictError, InsufficientFundsError, NotFoundError
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.routers.aircraft_families import build_family_out
from app.schemas.aircraft_family import AircraftFamilyOut
from app.schemas.airport import AirportOut
from app.services import license_service

router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.post("/airports/{airport_id}/unlock", response_model=AirportOut)
async def unlock_airport(
    airport_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AirportOut:
    try:
        airport = await license_service.unlock_airport(db, current_user.id, airport_id)
    except NotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_detail(exc)) from exc
    except ConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_detail(exc)) from exc
    except InsufficientFundsError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail(exc)) from exc
    await db.commit()
    return AirportOut(
        id=airport.id,
        icao4=airport.icao4,
        iata=airport.iata,
        name=airport.name,
        city=airport.city,
        country=airport.country,
        unlock_cost_credits=airport.unlock_cost_credits,
        unlocked=True,
    )


@router.post("/aircraft-families/{family_id}/unlock", response_model=AircraftFamilyOut)
async def unlock_aircraft_family(
    family_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AircraftFamilyOut:
    try:
        family = await license_service.unlock_aircraft_family(db, current_user.id, family_id)
    except NotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_detail(exc)) from exc
    except ConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_detail(exc)) from exc
    except InsufficientFundsError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail(exc)) from exc
    await db.commit()
    return await build_family_out(db, family, {family_id})
