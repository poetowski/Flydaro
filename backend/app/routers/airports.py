from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.airport import Airport
from app.models.user import User
from app.schemas.airport import AirportOut
from app.services import license_service

router = APIRouter(prefix="/airports", tags=["airports"])


@router.get("", response_model=list[AirportOut])
async def list_airports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AirportOut]:
    # Returns EVERY airport (locked and unlocked), annotated per-user -- this
    # is the single source for both the flight board's dropdown (client
    # filters to unlocked==true) and the Licenses page (shows everything).
    # NOTE: intentionally does not filter on Airport.is_active -- that flag
    # is a poller-scheduling detail ("does the worker watch this bbox"), not
    # a per-user access check. Every seeded airport is a valid roster entry.
    airports = list(await db.scalars(select(Airport)))
    unlocked_ids = await license_service.get_unlocked_airport_ids(db, current_user.id)
    return [
        AirportOut(
            id=airport.id,
            icao4=airport.icao4,
            iata=airport.iata,
            name=airport.name,
            city=airport.city,
            country=airport.country,
            unlock_cost_credits=airport.unlock_cost_credits,
            unlocked=airport.id in unlocked_ids,
        )
        for airport in airports
    ]
