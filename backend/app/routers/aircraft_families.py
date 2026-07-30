from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.aircraft_family import AircraftFamily
from app.models.user import User
from app.schemas.aircraft_family import AircraftFamilyMemberOut, AircraftFamilyOut
from app.services import license_service

router = APIRouter(prefix="/aircraft-families", tags=["aircraft-families"])


async def build_family_out(
    db: AsyncSession, family: AircraftFamily, unlocked_family_ids: set[int]
) -> AircraftFamilyOut:
    member_types = await license_service.get_family_member_types(db, family.id)
    return AircraftFamilyOut(
        id=family.id,
        code=family.code,
        name=family.name,
        unlock_cost_credits=family.unlock_cost_credits,
        unlocked=family.id in unlocked_family_ids,
        member_types=[
            AircraftFamilyMemberOut(id=t.id, icao_type_code=t.icao_type_code, name=t.name)
            for t in member_types
        ],
    )


@router.get("", response_model=list[AircraftFamilyOut])
async def list_aircraft_families(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AircraftFamilyOut]:
    # Deliberately includes locked families (needed so the flight board's
    # filter and the Licenses page can both show what's purchasable).
    families = list(
        await db.scalars(select(AircraftFamily).where(AircraftFamily.is_active.is_(True)))
    )
    unlocked_family_ids = await license_service.get_unlocked_family_ids(db, current_user.id)
    return [await build_family_out(db, family, unlocked_family_ids) for family in families]
