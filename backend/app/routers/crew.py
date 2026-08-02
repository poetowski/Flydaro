from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_detail import error_detail
from app.core.exceptions import InsufficientFundsError, LicenseRequiredError, NotFoundError
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.airport import Airport
from app.models.user import User
from app.schemas.crew import CrewOverviewEntryOut
from app.services import crew_service

router = APIRouter(prefix="/crew", tags=["crew"])


@router.get("", response_model=list[CrewOverviewEntryOut])
async def get_crew_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CrewOverviewEntryOut]:
    overview = await crew_service.get_crew_overview(db, current_user.id)
    return [
        CrewOverviewEntryOut(
            airport_id=airport.id,
            icao4=airport.icao4,
            name=airport.name,
            crew_count=crew_count,
            busy_count=busy_count,
            free_count=crew_count - busy_count,
            next_hire_cost=crew_service.hire_cost(crew_count),
        )
        for airport, crew_count, busy_count in overview
    ]


@router.post("/{airport_id}/hire", response_model=CrewOverviewEntryOut)
async def hire_crew(
    airport_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CrewOverviewEntryOut:
    try:
        crew = await crew_service.hire_crew(db, current_user.id, airport_id)
    except NotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_detail(exc)) from exc
    except LicenseRequiredError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_detail(exc)) from exc
    except InsufficientFundsError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail(exc)) from exc
    await db.commit()

    airport = await db.get(Airport, airport_id)
    busy_count = await crew_service.count_busy_rentals(db, current_user.id, airport_id)
    return CrewOverviewEntryOut(
        airport_id=airport.id,
        icao4=airport.icao4,
        name=airport.name,
        crew_count=crew.crew_count,
        busy_count=busy_count,
        free_count=crew.crew_count - busy_count,
        next_hire_cost=crew_service.hire_cost(crew.crew_count),
    )
