import random
import string
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CapacityClosedError,
    ConflictError,
    CrewUnavailableError,
    LicenseRequiredError,
    NotFoundError,
    RentalNotResolvedError,
)
from app.models.aircraft import AircraftType
from app.models.aircraft_family import AircraftFamily
from app.models.airport import Airport
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.models.item_type import ItemType
from app.models.rental import Rental, RentalStatus
from app.models.wallet import LedgerReason
from app.services import crew_service, license_service, settlement_service
from app.services.wallet_service import apply_ledger_entry

# Excludes visually ambiguous characters (0/O, 1/I).
DISPLAY_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "O0I1")
DISPLAY_CODE_SUFFIX_LENGTH = 5
MAX_DISPLAY_CODE_ATTEMPTS = 5


def generate_display_code(departure_at: datetime) -> str:
    """Human-readable rental name: the flight's departure time (not the
    rental's own placement time, so multiple rentals on the same flight
    share a recognizable prefix) plus a random suffix, e.g.
    "20260801-1423-7QXK"."""
    suffix = "".join(random.choices(DISPLAY_CODE_ALPHABET, k=DISPLAY_CODE_SUFFIX_LENGTH))
    return f"{departure_at.strftime('%Y%m%d-%H%M')}-{suffix}"


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

    crew_count = await crew_service.get_crew_count(db, user_id, airport.id)
    busy_count = await crew_service.count_busy_rentals(db, user_id, airport.id)
    if busy_count >= crew_count:
        raise CrewUnavailableError(
            "No free crew members at this airport -- all are currently assigned"
        )

    item_type = await db.get(ItemType, item_type_id)
    if item_type is None or not item_type.is_active:
        raise NotFoundError("Item type not found")

    # Insert-first with a fresh random display_code each attempt: the unique
    # constraint is the real guarantee, this retry is just cheap insurance
    # against an astronomically unlikely collision (~33M combinations per
    # departure-minute bucket) -- same begin_nested/IntegrityError pattern
    # as license_service's unlock functions.
    rental: Rental | None = None
    for _ in range(MAX_DISPLAY_CODE_ATTEMPTS):
        try:
            async with db.begin_nested():
                rental = Rental(
                    user_id=user_id,
                    tracked_flight_id=tracked_flight_id,
                    item_type_id=item_type_id,
                    rental_fee_credits=rental_fee_credits,
                    status=RentalStatus.FLYING,
                    display_code=generate_display_code(flight.first_seen_at),
                )
                db.add(rental)
                await db.flush()
            break
        except IntegrityError:
            rental = None
    if rental is None:
        raise ConflictError("Could not generate a unique rental code, please retry")

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


async def get_display_info_for_rentals(
    db: AsyncSession, rental_ids: list[int]
) -> dict[int, tuple[str | None, str | None]]:
    """Maps rental_id -> (origin_airport_code, aircraft_family_code) via one
    join query -- avoids an N+1 per-rental lookup when the API needs this for
    display (e.g. the frontend's origin-airport/aircraft-family ribbons).
    Both are None if the underlying flight's aircraft type never resolved a
    family (shouldn't happen for a real rental, since creating one requires
    an unlocked family, but the join is a plain LEFT JOIN so it degrades to
    None rather than dropping the row)."""
    if not rental_ids:
        return {}
    stmt = (
        select(Rental.id, Airport.icao4, AircraftFamily.code)
        .join(TrackedFlight, TrackedFlight.id == Rental.tracked_flight_id)
        .join(Airport, Airport.id == TrackedFlight.origin_airport_id)
        .outerjoin(AircraftType, AircraftType.id == TrackedFlight.aircraft_type_id)
        .outerjoin(AircraftFamily, AircraftFamily.id == AircraftType.family_id)
        .where(Rental.id.in_(rental_ids))
    )
    result = await db.execute(stmt)
    return {rental_id: (airport_code, family_code) for rental_id, airport_code, family_code in result.all()}


async def lock_capacity(db: AsyncSession, flight: TrackedFlight) -> None:
    """Rental window closed: flight keeps flying, existing rentals become IN_PROGRESS."""
    flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    flight.capacity_open = False

    rentals = await db.scalars(
        select(Rental).where(Rental.tracked_flight_id == flight.id, Rental.status == RentalStatus.FLYING)
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
    """Terminal transition. Computes and stores each rental's settlement
    (still open on this flight, regardless of whether it went through
    RESOLVING or hit a ceiling directly) but does NOT credit the wallet --
    the reward is claimable, not automatic. See claim_rental() for the
    explicit action that actually credits it.
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
            Rental.status.in_([RentalStatus.FLYING, RentalStatus.IN_PROGRESS, RentalStatus.RESOLVING]),
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

    await db.flush()


async def claim_rental(db: AsyncSession, user_id: int, rental_id: int) -> Rental:
    """The only place a rental's reward actually reaches the wallet --
    explicit player action, gated on the flight having already resolved."""
    rental = await get_rental_for_user(db, user_id, rental_id)
    if rental.status == RentalStatus.CLAIMED:
        raise ConflictError("Reward already claimed")
    if rental.status != RentalStatus.RESOLVED:
        raise RentalNotResolvedError("This rental's flight has not resolved yet")

    await apply_ledger_entry(
        db, user_id, rental.settlement_credits, LedgerReason.SETTLEMENT, related_rental_id=rental.id
    )
    rental.status = RentalStatus.CLAIMED
    rental.claimed_at = datetime.now(timezone.utc)
    await db.flush()
    return rental
