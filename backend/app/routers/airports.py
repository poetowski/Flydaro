from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.airport import Airport
from app.models.user import User
from app.schemas.airport import AirportOut

router = APIRouter(prefix="/airports", tags=["airports"])


@router.get("", response_model=list[AirportOut])
async def list_airports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Airport]:
    result = await db.scalars(select(Airport).where(Airport.is_active.is_(True)))
    return list(result.all())
