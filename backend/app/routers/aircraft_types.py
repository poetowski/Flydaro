from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.aircraft import AircraftType
from app.models.user import User
from app.schemas.aircraft import AircraftTypeOut

router = APIRouter(prefix="/aircraft-types", tags=["aircraft-types"])


@router.get("", response_model=list[AircraftTypeOut])
async def list_aircraft_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AircraftType]:
    # Purely a name-resolution list now (licensing lives on aircraft_families,
    # see routers/aircraft_families.py) -- used to display a flight's
    # specific real model, e.g. "Airbus A321neo," regardless of which
    # family filter is currently selected on the board.
    return list(await db.scalars(select(AircraftType).where(AircraftType.is_active.is_(True))))
