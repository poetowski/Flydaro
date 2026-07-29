from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.item_type import ItemType
from app.models.user import User
from app.schemas.item_type import ItemTypeOut

router = APIRouter(prefix="/item-types", tags=["item-types"])


@router.get("", response_model=list[ItemTypeOut])
async def list_item_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ItemType]:
    result = await db.scalars(select(ItemType).where(ItemType.is_active.is_(True)))
    return list(result.all())
