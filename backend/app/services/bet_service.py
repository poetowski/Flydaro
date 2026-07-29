from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BettingClosedError, NotFoundError
from app.models.bet import Bet, BetStatus
from app.models.cargo import CargoType
from app.models.flight import TrackedFlight, TrackedFlightStatus
from app.models.wallet import LedgerReason
from app.services import payout_service
from app.services.wallet_service import apply_ledger_entry


async def place_bet(
    db: AsyncSession,
    user_id: int,
    tracked_flight_id: int,
    cargo_type_id: int,
    stake_credits: int,
) -> Bet:
    flight = await db.get(TrackedFlight, tracked_flight_id)
    if flight is None:
        raise NotFoundError("Flight not found")
    if not flight.bets_open or flight.status != TrackedFlightStatus.AIRBORNE_OPEN:
        raise BettingClosedError("Betting has closed for this flight")

    cargo_type = await db.get(CargoType, cargo_type_id)
    if cargo_type is None or not cargo_type.is_active:
        raise NotFoundError("Cargo type not found")

    bet = Bet(
        user_id=user_id,
        tracked_flight_id=tracked_flight_id,
        cargo_type_id=cargo_type_id,
        stake_credits=stake_credits,
        status=BetStatus.PENDING,
    )
    db.add(bet)
    await db.flush()

    # Raises InsufficientFundsError (propagated to the router) if the wallet
    # can't cover the stake; the flushed-but-uncommitted bet row is rolled
    # back by the router in that case.
    await apply_ledger_entry(
        db, user_id, -stake_credits, LedgerReason.BET_STAKE, related_bet_id=bet.id
    )

    return bet


async def get_bet_for_user(db: AsyncSession, user_id: int, bet_id: int) -> Bet:
    bet = await db.scalar(select(Bet).where(Bet.id == bet_id, Bet.user_id == user_id))
    if bet is None:
        raise NotFoundError("Bet not found")
    return bet


async def list_bets_for_user(
    db: AsyncSession, user_id: int, status: BetStatus | None = None
) -> list[Bet]:
    stmt = select(Bet).where(Bet.user_id == user_id).order_by(Bet.placed_at.desc())
    if status is not None:
        stmt = stmt.where(Bet.status == status)
    result = await db.scalars(stmt)
    return list(result.all())


async def lock_betting(db: AsyncSession, flight: TrackedFlight) -> None:
    """Betting window closed: flight keeps flying, existing bets become IN_PROGRESS."""
    flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    flight.bets_open = False

    bets = await db.scalars(
        select(Bet).where(Bet.tracked_flight_id == flight.id, Bet.status == BetStatus.PENDING)
    )
    for bet in bets:
        bet.status = BetStatus.IN_PROGRESS
    await db.flush()


async def mark_landing_suspected(db: AsyncSession, flight: TrackedFlight, observed_at: datetime) -> None:
    flight.status = TrackedFlightStatus.LANDING_SUSPECTED
    flight.landing_suspected_at = observed_at

    bets = await db.scalars(
        select(Bet).where(
            Bet.tracked_flight_id == flight.id, Bet.status == BetStatus.IN_PROGRESS
        )
    )
    for bet in bets:
        bet.status = BetStatus.RESOLVING
    await db.flush()


async def rollback_landing_suspected(db: AsyncSession, flight: TrackedFlight) -> None:
    """False alarm (touch-and-go / go-around): back to locked and in-progress."""
    flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    flight.landing_suspected_at = None

    bets = await db.scalars(
        select(Bet).where(Bet.tracked_flight_id == flight.id, Bet.status == BetStatus.RESOLVING)
    )
    for bet in bets:
        bet.status = BetStatus.IN_PROGRESS
    await db.flush()


async def resolve_tracked_flight(
    db: AsyncSession,
    flight: TrackedFlight,
    status: TrackedFlightStatus,
    resolution_reason: str,
    resolution_summary: dict,
    resolved_at: datetime | None = None,
) -> None:
    """Terminal transition. Pays out every bet still open on this flight,
    regardless of whether it went through RESOLVING or hit a ceiling directly.
    """
    resolved_at = resolved_at or datetime.now(timezone.utc)
    flight.status = status
    flight.resolved_at = resolved_at
    flight.resolution_summary = resolution_summary
    flight.bets_open = False

    duration_minutes = (resolved_at - flight.first_seen_at).total_seconds() / 60

    bets = await db.scalars(
        select(Bet).where(
            Bet.tracked_flight_id == flight.id,
            Bet.status.in_([BetStatus.PENDING, BetStatus.IN_PROGRESS, BetStatus.RESOLVING]),
        )
    )
    cargo_multiplier_cache: dict[int, float] = {}
    for bet in bets:
        if bet.cargo_type_id not in cargo_multiplier_cache:
            cargo_type = await db.get(CargoType, bet.cargo_type_id)
            cargo_multiplier_cache[bet.cargo_type_id] = float(cargo_type.payout_multiplier)
        cargo_multiplier = cargo_multiplier_cache[bet.cargo_type_id]

        payout_credits, breakdown = payout_service.compute_payout(
            bet.stake_credits, duration_minutes, cargo_multiplier, resolution_reason
        )

        bet.status = BetStatus.RESOLVED
        bet.resolved_at = resolved_at
        bet.payout_credits = payout_credits
        bet.payout_breakdown = breakdown
        bet.resolution_reason = resolution_reason

        await apply_ledger_entry(
            db, bet.user_id, payout_credits, LedgerReason.BET_PAYOUT, related_bet_id=bet.id
        )

    await db.flush()
