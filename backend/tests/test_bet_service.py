from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import (
    BettingClosedError,
    InsufficientFundsError,
    LicenseRequiredError,
    NotFoundError,
)
from app.models.bet import BetStatus
from app.models.flight import TrackedFlightStatus
from app.services import bet_service
from app.services.payout_service import LANDED_REASON, LOST_SIGNAL_REASON
from app.services.wallet_service import apply_ledger_entry, get_balance
from app.models.wallet import LedgerReason


async def _fund(db, user, amount=2000):
    await apply_ledger_entry(db, user.id, amount, LedgerReason.SIGNUP_BONUS)


async def test_place_bet_debits_wallet_and_creates_pending_bet(db, user, open_flight, cargo_type):
    await _fund(db, user)
    bet = await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)
    assert bet.status == BetStatus.PENDING
    assert await get_balance(db, user.id) == 1700


async def test_place_bet_insufficient_funds_raises(db, user, open_flight, cargo_type):
    await _fund(db, user, amount=100)
    with pytest.raises(InsufficientFundsError):
        await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)


async def test_place_bet_on_locked_flight_raises(db, user, open_flight, cargo_type):
    await _fund(db, user)
    open_flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    open_flight.bets_open = False
    with pytest.raises(BettingClosedError):
        await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)


async def test_place_bet_unknown_flight_raises(db, user, cargo_type):
    await _fund(db, user)
    with pytest.raises(NotFoundError):
        await bet_service.place_bet(db, user.id, 999, cargo_type.id, 300)


async def test_place_bet_unresolved_aircraft_type_raises(db, user, open_flight, cargo_type):
    await _fund(db, user)
    open_flight.aircraft_type_id = None
    with pytest.raises(LicenseRequiredError):
        await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)


async def test_place_bet_locked_aircraft_type_raises(
    db, user, open_flight, cargo_type, locked_aircraft_type
):
    await _fund(db, user)
    open_flight.aircraft_type_id = locked_aircraft_type.id
    with pytest.raises(LicenseRequiredError):
        await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)


async def test_place_bet_locked_airport_raises(
    db, user, open_flight, cargo_type, locked_airport
):
    await _fund(db, user)
    open_flight.origin_airport_id = locked_airport.id
    with pytest.raises(LicenseRequiredError):
        await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)


async def test_lock_betting_transitions_pending_bets_to_in_progress(db, user, open_flight, cargo_type):
    await _fund(db, user)
    bet = await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)

    await bet_service.lock_betting(db, open_flight)

    assert open_flight.status == TrackedFlightStatus.AIRBORNE_LOCKED
    assert open_flight.bets_open is False
    refreshed = await bet_service.get_bet_for_user(db, user.id, bet.id)
    assert refreshed.status == BetStatus.IN_PROGRESS


async def test_landing_suspected_then_rollback_returns_bet_to_in_progress(db, user, open_flight, cargo_type):
    await _fund(db, user)
    bet = await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)
    await bet_service.lock_betting(db, open_flight)

    now = datetime.now(timezone.utc)
    await bet_service.mark_landing_suspected(db, open_flight, now)
    refreshed = await bet_service.get_bet_for_user(db, user.id, bet.id)
    assert refreshed.status == BetStatus.RESOLVING

    await bet_service.rollback_landing_suspected(db, open_flight)
    assert open_flight.status == TrackedFlightStatus.AIRBORNE_LOCKED
    refreshed = await bet_service.get_bet_for_user(db, user.id, bet.id)
    assert refreshed.status == BetStatus.IN_PROGRESS


async def test_resolve_tracked_flight_pays_out_and_credits_wallet(db, user, open_flight, cargo_type):
    await _fund(db, user)
    bet = await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)
    await bet_service.lock_betting(db, open_flight)

    resolved_at = open_flight.first_seen_at + timedelta(minutes=30)
    await bet_service.resolve_tracked_flight(
        db,
        open_flight,
        TrackedFlightStatus.RESOLVED_LANDED,
        LANDED_REASON,
        {"note": "test"},
        resolved_at=resolved_at,
    )

    refreshed = await bet_service.get_bet_for_user(db, user.id, bet.id)
    assert refreshed.status == BetStatus.RESOLVED
    assert refreshed.payout_credits == round(300 * 1.2 * 1.10)  # <60min bucket * cargo multiplier
    # balance = 2000 - 300 stake + payout
    assert await get_balance(db, user.id) == 2000 - 300 + refreshed.payout_credits


async def test_resolve_tracked_flight_fallback_pays_less_than_clean_landing(db, user, open_flight, cargo_type):
    await _fund(db, user)
    bet = await bet_service.place_bet(db, user.id, open_flight.id, cargo_type.id, 300)
    await bet_service.lock_betting(db, open_flight)

    resolved_at = open_flight.first_seen_at + timedelta(minutes=30)
    await bet_service.resolve_tracked_flight(
        db,
        open_flight,
        TrackedFlightStatus.RESOLVED_LOST_SIGNAL,
        LOST_SIGNAL_REASON,
        {"note": "vanished"},
        resolved_at=resolved_at,
    )

    refreshed = await bet_service.get_bet_for_user(db, user.id, bet.id)
    assert refreshed.resolution_reason == LOST_SIGNAL_REASON
    assert refreshed.payout_credits < round(300 * 1.2 * 1.10)
