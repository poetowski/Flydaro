from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.aircraft import AircraftType
from app.models.airport import Airport
from app.models.license import UserAircraftTypeUnlock, UserAirportUnlock
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


async def get_unlocked_aircraft_type_ids(db: AsyncSession, user_id: int) -> set[int]:
    unlocked_subquery = select(UserAircraftTypeUnlock.aircraft_type_id).where(
        UserAircraftTypeUnlock.user_id == user_id
    )
    stmt = select(AircraftType.id).where(
        or_(AircraftType.is_starter.is_(True), AircraftType.id.in_(unlocked_subquery))
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
    if aircraft_type is None:
        return False
    if aircraft_type.is_starter:
        return True
    unlock = await db.get(UserAircraftTypeUnlock, (user_id, aircraft_type_id))
    return unlock is not None


async def unlock_airport(db: AsyncSession, user_id: int, airport_id: int) -> Airport:
    airport = await db.get(Airport, airport_id)
    if airport is None:
        raise NotFoundError("Airport not found")
    if airport.is_starter:
        raise ConflictError("Airport is already unlocked for everyone")

    # Insert-first: the composite PK fails fast on a duplicate/racing
    # request, before any wallet debit happens -- the losing side of a race
    # never reaches apply_ledger_entry, so no double-charge is possible.
    try:
        async with db.begin_nested():
            db.add(UserAirportUnlock(user_id=user_id, airport_id=airport_id))
            await db.flush()
    except IntegrityError as exc:
        raise ConflictError("Airport already unlocked") from exc

    await apply_ledger_entry(
        db, user_id, -airport.unlock_cost_credits, LedgerReason.LICENSE_PURCHASE
    )

    # Global, poller-scoped flag: once any player unlocks this airport, the
    # worker should start watching it for everyone on its next tick.
    if not airport.is_active:
        airport.is_active = True

    await db.flush()
    return airport


async def unlock_aircraft_type(db: AsyncSession, user_id: int, aircraft_type_id: int) -> AircraftType:
    aircraft_type = await db.get(AircraftType, aircraft_type_id)
    if aircraft_type is None:
        raise NotFoundError("Aircraft type not found")
    if aircraft_type.is_starter:
        raise ConflictError("Aircraft type is already unlocked for everyone")

    try:
        async with db.begin_nested():
            db.add(UserAircraftTypeUnlock(user_id=user_id, aircraft_type_id=aircraft_type_id))
            await db.flush()
    except IntegrityError as exc:
        raise ConflictError("Aircraft type already unlocked") from exc

    await apply_ledger_entry(
        db, user_id, -aircraft_type.unlock_cost_credits, LedgerReason.LICENSE_PURCHASE
    )

    await db.flush()
    return aircraft_type
