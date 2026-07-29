from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.cargo import CargoType
from app.models.user import User
from app.schemas.cargo import CargoTypeOut

router = APIRouter(prefix="/cargo-types", tags=["cargo"])


@router.get("", response_model=list[CargoTypeOut])
async def list_cargo_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CargoType]:
    result = await db.scalars(select(CargoType).where(CargoType.is_active.is_(True)))
    return list(result.all())
