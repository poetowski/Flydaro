from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LicenseRequiredError, NotFoundError
from app.models.airport import Airport
from app.models.crew import UserAirportCrew
from app.models.flight import TrackedFlight
from app.models.rental import Rental, RentalStatus
from app.models.wallet import LedgerReason
from app.services import license_service
from app.services.wallet_service import apply_ledger_entry

# Adjustable default, like every other seeded economy number in this
# codebase. Scales with how many crew already exist at that specific
# airport: 1st hire there costs this much, 2nd costs double, etc.
CREW_BASE_COST_CREDITS = 300

# A rental still ties up its origin airport's crew member until its flight
# resolves -- claiming the reward afterward is a separate wallet action
# that doesn't affect crew availability.
_BUSY_STATUSES = (
    RentalStatus.FLYING,
    RentalStatus.IN_PROGRESS,
    RentalStatus.RESOLVING,
)


def hire_cost(existing_crew_count: int) -> int:
    return CREW_BASE_COST_CREDITS * (existing_crew_count + 1)


async def get_crew_count(db: AsyncSession, user_id: int, airport_id: int) -> int:
    crew = await db.get(UserAirportCrew, (user_id, airport_id))
    return crew.crew_count if crew else 0


async def count_busy_rentals(db: AsyncSession, user_id: int, airport_id: int) -> int:
    """How many of this user's rentals originating from this airport are
    still tying up a crew member -- derived from rentals/tracked_flights
    directly rather than stored, so there's no separate "allocation" state
    that could ever drift out of sync."""
    count = await db.scalar(
        select(func.count())
        .select_from(Rental)
        .join(TrackedFlight, TrackedFlight.id == Rental.tracked_flight_id)
        .where(
            Rental.user_id == user_id,
            TrackedFlight.origin_airport_id == airport_id,
            Rental.status.in_(_BUSY_STATUSES),
        )
    )
    return count or 0


async def get_crew_overview(db: AsyncSession, user_id: int) -> list[tuple[Airport, int, int]]:
    """(airport, crew_count, busy_count) for every airport this user has
    unlocked -- including ones they've never hired crew for (0 crew), via
    a LEFT JOIN rather than only returning existing user_airport_crew rows."""
    unlocked_ids = await license_service.get_unlocked_airport_ids(db, user_id)
    if not unlocked_ids:
        return []

    result = await db.execute(
        select(Airport, func.coalesce(UserAirportCrew.crew_count, 0))
        .outerjoin(
            UserAirportCrew,
            (UserAirportCrew.airport_id == Airport.id) & (UserAirportCrew.user_id == user_id),
        )
        .where(Airport.id.in_(unlocked_ids))
        .order_by(Airport.name)
    )
    overview = []
    for airport, crew_count in result.all():
        busy_count = await count_busy_rentals(db, user_id, airport.id)
        overview.append((airport, crew_count, busy_count))
    return overview


async def hire_crew(db: AsyncSession, user_id: int, airport_id: int) -> UserAirportCrew:
    airport = await db.get(Airport, airport_id)
    if airport is None:
        raise NotFoundError("Airport not found")
    if not await license_service.user_has_airport_unlock(db, user_id, airport):
        raise LicenseRequiredError("You must unlock this airport before hiring crew there")

    crew = await db.get(UserAirportCrew, (user_id, airport_id))
    current_count = crew.crew_count if crew else 0
    cost = hire_cost(current_count)

    await apply_ledger_entry(db, user_id, -cost, LedgerReason.CREW_HIRE)

    if crew is None:
        crew = UserAirportCrew(user_id=user_id, airport_id=airport_id, crew_count=1)
        db.add(crew)
    else:
        crew.crew_count = current_count + 1

    await db.flush()
    return crew
