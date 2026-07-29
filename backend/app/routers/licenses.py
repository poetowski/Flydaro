from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, InsufficientFundsError, NotFoundError
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.aircraft import AircraftTypeOut
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InsufficientFundsError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
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


@router.post("/aircraft-types/{aircraft_type_id}/unlock", response_model=AircraftTypeOut)
async def unlock_aircraft_type(
    aircraft_type_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AircraftTypeOut:
    try:
        aircraft_type = await license_service.unlock_aircraft_type(
            db, current_user.id, aircraft_type_id
        )
    except NotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InsufficientFundsError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return AircraftTypeOut(
        id=aircraft_type.id,
        icao_type_code=aircraft_type.icao_type_code,
        name=aircraft_type.name,
        manufacturer=aircraft_type.manufacturer,
        unlock_cost_credits=aircraft_type.unlock_cost_credits,
        unlocked=True,
    )
