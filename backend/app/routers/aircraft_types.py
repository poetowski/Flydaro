from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.aircraft import AircraftType
from app.models.user import User
from app.schemas.aircraft import AircraftTypeOut
from app.services import license_service

router = APIRouter(prefix="/aircraft-types", tags=["aircraft-types"])


@router.get("", response_model=list[AircraftTypeOut])
async def list_aircraft_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AircraftTypeOut]:
    # Deliberately includes locked types (needed so the flight board's type
    # filter can reference a known-but-locked type, and so the Licenses page
    # can render them for purchase).
    aircraft_types = list(
        await db.scalars(select(AircraftType).where(AircraftType.is_active.is_(True)))
    )
    unlocked_ids = await license_service.get_unlocked_aircraft_type_ids(db, current_user.id)
    return [
        AircraftTypeOut(
            id=aircraft_type.id,
            icao_type_code=aircraft_type.icao_type_code,
            name=aircraft_type.name,
            manufacturer=aircraft_type.manufacturer,
            unlock_cost_credits=aircraft_type.unlock_cost_credits,
            unlocked=aircraft_type.id in unlocked_ids,
        )
        for aircraft_type in aircraft_types
    ]
