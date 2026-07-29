from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CapacityClosedError, LicenseRequiredError, NotFoundError
from app.models.airport import Airport
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.models.item_type import ItemType
from app.models.rental import Rental, RentalStatus
from app.models.wallet import LedgerReason
from app.services import license_service, settlement_service
from app.services.wallet_service import apply_ledger_entry


async def create_rental(
    db: AsyncSession,
    user_id: int,
    tracked_flight_id: int,
    item_type_id: int,
    rental_fee_credits: int,
) -> Rental:
    flight = await db.get(TrackedFlight, tracked_flight_id)
    if flight is None:
        raise NotFoundError("Flight not found")
    if not flight.capacity_open or flight.status != TrackedFlightStatus.AIRBORNE_OPEN:
        raise CapacityClosedError("Capacity on this flight is no longer available to rent")

    airport = await db.get(Airport, flight.origin_airport_id)
    if not await license_service.user_has_airport_unlock(db, user_id, airport):
        raise LicenseRequiredError("You have not unlocked this airport")

    if flight.aircraft_type_id is None:
        raise LicenseRequiredError("This flight's aircraft type could not be identified")
    if not await license_service.user_has_aircraft_type_unlock(
        db, user_id, flight.aircraft_type_id
    ):
        raise LicenseRequiredError("You have not unlocked this aircraft type")

    item_type = await db.get(ItemType, item_type_id)
    if item_type is None or not item_type.is_active:
        raise NotFoundError("Item type not found")

    rental = Rental(
        user_id=user_id,
        tracked_flight_id=tracked_flight_id,
        item_type_id=item_type_id,
        rental_fee_credits=rental_fee_credits,
        status=RentalStatus.PENDING,
    )
    db.add(rental)
    await db.flush()

    # Raises InsufficientFundsError (propagated to the router) if the wallet
    # can't cover the fee; the flushed-but-uncommitted rental row is rolled
    # back by the router in that case.
    await apply_ledger_entry(
        db, user_id, -rental_fee_credits, LedgerReason.RENTAL_FEE, related_rental_id=rental.id
    )

    return rental


async def get_rental_for_user(db: AsyncSession, user_id: int, rental_id: int) -> Rental:
    rental = await db.scalar(select(Rental).where(Rental.id == rental_id, Rental.user_id == user_id))
    if rental is None:
        raise NotFoundError("Rental not found")
    return rental


async def list_rentals_for_user(
    db: AsyncSession, user_id: int, status: RentalStatus | None = None
) -> list[Rental]:
    stmt = select(Rental).where(Rental.user_id == user_id).order_by(Rental.rented_at.desc())
    if status is not None:
        stmt = stmt.where(Rental.status == status)
    result = await db.scalars(stmt)
    return list(result.all())


async def lock_capacity(db: AsyncSession, flight: TrackedFlight) -> None:
    """Rental window closed: flight keeps flying, existing rentals become IN_PROGRESS."""
    flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    flight.capacity_open = False

    rentals = await db.scalars(
        select(Rental).where(Rental.tracked_flight_id == flight.id, Rental.status == RentalStatus.PENDING)
    )
    for rental in rentals:
        rental.status = RentalStatus.IN_PROGRESS
    await db.flush()


async def mark_landing_suspected(db: AsyncSession, flight: TrackedFlight, observed_at: datetime) -> None:
    flight.status = TrackedFlightStatus.LANDING_SUSPECTED
    flight.landing_suspected_at = observed_at

    rentals = await db.scalars(
        select(Rental).where(
            Rental.tracked_flight_id == flight.id, Rental.status == RentalStatus.IN_PROGRESS
        )
    )
    for rental in rentals:
        rental.status = RentalStatus.RESOLVING
    await db.flush()


async def rollback_landing_suspected(db: AsyncSession, flight: TrackedFlight) -> None:
    """False alarm (touch-and-go / go-around): back to locked and in-progress."""
    flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    flight.landing_suspected_at = None

    rentals = await db.scalars(
        select(Rental).where(Rental.tracked_flight_id == flight.id, Rental.status == RentalStatus.RESOLVING)
    )
    for rental in rentals:
        rental.status = RentalStatus.IN_PROGRESS
    await db.flush()


async def resolve_tracked_flight(
    db: AsyncSession,
    flight: TrackedFlight,
    status: TrackedFlightStatus,
    resolution_reason: str,
    resolution_summary: dict,
    resolved_at: datetime | None = None,
) -> None:
    """Terminal transition. Settles every rental still open on this flight,
    regardless of whether it went through RESOLVING or hit a ceiling directly.
    """
    resolved_at = resolved_at or datetime.now(timezone.utc)
    flight.status = status
    flight.resolved_at = resolved_at
    flight.resolution_summary = resolution_summary
    flight.capacity_open = False

    duration_minutes = (resolved_at - flight.first_seen_at).total_seconds() / 60

    rentals = await db.scalars(
        select(Rental).where(
            Rental.tracked_flight_id == flight.id,
            Rental.status.in_([RentalStatus.PENDING, RentalStatus.IN_PROGRESS, RentalStatus.RESOLVING]),
        )
    )
    item_multiplier_cache: dict[int, float] = {}
    for rental in rentals:
        if rental.item_type_id not in item_multiplier_cache:
            item_type = await db.get(ItemType, rental.item_type_id)
            item_multiplier_cache[rental.item_type_id] = float(item_type.settlement_multiplier)
        item_multiplier = item_multiplier_cache[rental.item_type_id]

        settlement_credits, breakdown = settlement_service.compute_settlement(
            rental.rental_fee_credits, duration_minutes, item_multiplier, resolution_reason
        )

        rental.status = RentalStatus.RESOLVED
        rental.resolved_at = resolved_at
        rental.settlement_credits = settlement_credits
        rental.settlement_breakdown = breakdown
        rental.resolution_reason = resolution_reason

        await apply_ledger_entry(
            db, rental.user_id, settlement_credits, LedgerReason.SETTLEMENT, related_rental_id=rental.id
        )

    await db.flush()
