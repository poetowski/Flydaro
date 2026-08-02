from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.aircraft import AircraftType
from app.models.aircraft_family import AircraftFamily
from app.models.airport import Airport
from app.models.license import UserAircraftFamilyUnlock, UserAirportUnlock
from app.models.wallet import LedgerReason
from app.services.wallet_service import apply_ledger_entry


async def get_unlocked_airport_ids(db: AsyncSession, user_id: int) -> set[int]:
    unlocked_subquery = select(UserAirportUnlock.airport_id).where(
        UserAirportUnlock.user_id == user_id
    )
    stmt = select(Airport.id).where(
        or_(Airport.is_starter.is_(True), Airport.id.in_(unlocked_subquery))
    )
    return set(await db.scalars(stmt))


async def get_unlocked_family_ids(db: AsyncSession, user_id: int) -> set[int]:
    unlocked_subquery = select(UserAircraftFamilyUnlock.family_id).where(
        UserAircraftFamilyUnlock.user_id == user_id
    )
    stmt = select(AircraftFamily.id).where(
        or_(AircraftFamily.is_starter.is_(True), AircraftFamily.id.in_(unlocked_subquery))
    )
    return set(await db.scalars(stmt))


async def expand_family_to_type_ids(db: AsyncSession, family_id: int) -> set[int]:
    stmt = select(AircraftType.id).where(
        AircraftType.family_id == family_id, AircraftType.is_active.is_(True)
    )
    return set(await db.scalars(stmt))


async def get_family_member_types(db: AsyncSession, family_id: int) -> list[AircraftType]:
    stmt = select(AircraftType).where(
        AircraftType.family_id == family_id, AircraftType.is_active.is_(True)
    )
    return list(await db.scalars(stmt))


async def get_unlocked_aircraft_type_ids(db: AsyncSession, user_id: int) -> set[int]:
    """Individual AircraftType ids, not families -- kept as this exact name/
    shape since callers (flights.py's board floor, rental_service's gate)
    still operate on individual type ids. Licensing itself is family-level:
    this expands every unlocked family to its member types under the hood.
    """
    unlocked_family_ids = await get_unlocked_family_ids(db, user_id)
    if not unlocked_family_ids:
        return set()
    stmt = select(AircraftType.id).where(
        AircraftType.family_id.in_(unlocked_family_ids), AircraftType.is_active.is_(True)
    )
    return set(await db.scalars(stmt))


async def user_has_airport_unlock(db: AsyncSession, user_id: int, airport: Airport) -> bool:
    if airport.is_starter:
        return True
    unlock = await db.get(UserAirportUnlock, (user_id, airport.id))
    return unlock is not None


async def user_has_aircraft_type_unlock(
    db: AsyncSession, user_id: int, aircraft_type_id: int
) -> bool:
    aircraft_type = await db.get(AircraftType, aircraft_type_id)
    if aircraft_type is None or aircraft_type.family_id is None:
        return False
    family = await db.get(AircraftFamily, aircraft_type.family_id)
    if family.is_starter:
        return True
    unlock = await db.get(UserAircraftFamilyUnlock, (user_id, aircraft_type.family_id))
    return unlock is not None


async def unlock_airport(db: AsyncSession, user_id: int, airport_id: int) -> Airport:
    airport = await db.get(Airport, airport_id)
    if airport is None:
        raise NotFoundError("Airport not found", code="AIRPORT_NOT_FOUND")
    if airport.is_starter:
        raise ConflictError("Airport is already unlocked for everyone", code="AIRPORT_GLOBALLY_UNLOCKED")

    # Insert-first: the composite PK fails fast on a duplicate/racing
    # request, before any wallet debit happens -- the losing side of a race
    # never reaches apply_ledger_entry, so no double-charge is possible.
    try:
        async with db.begin_nested():
            db.add(UserAirportUnlock(user_id=user_id, airport_id=airport_id))
            await db.flush()
    except IntegrityError as exc:
        raise ConflictError("Airport already unlocked", code="AIRPORT_ALREADY_UNLOCKED") from exc

    await apply_ledger_entry(
        db, user_id, -airport.unlock_cost_credits, LedgerReason.LICENSE_PURCHASE
    )

    # Global, poller-scoped flag: once any player unlocks this airport, the
    # worker should start watching it for everyone on its next tick.
    if not airport.is_active:
        airport.is_active = True

    await db.flush()
    return airport


async def unlock_aircraft_family(db: AsyncSession, user_id: int, family_id: int) -> AircraftFamily:
    family = await db.get(AircraftFamily, family_id)
    if family is None:
        raise NotFoundError("Aircraft family not found", code="AIRCRAFT_FAMILY_NOT_FOUND")
    if family.is_starter:
        raise ConflictError(
            "Aircraft family is already unlocked for everyone", code="AIRCRAFT_FAMILY_GLOBALLY_UNLOCKED"
        )

    try:
        async with db.begin_nested():
            db.add(UserAircraftFamilyUnlock(user_id=user_id, family_id=family_id))
            await db.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "Aircraft family already unlocked", code="AIRCRAFT_FAMILY_ALREADY_UNLOCKED"
        ) from exc

    await apply_ledger_entry(
        db, user_id, -family.unlock_cost_credits, LedgerReason.LICENSE_PURCHASE
    )

    await db.flush()
    return family
