from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import (
    CapacityClosedError,
    ConflictError,
    InsufficientFundsError,
    LicenseRequiredError,
    NotFoundError,
    RentalNotResolvedError,
)
from app.models.rental import RentalStatus
from app.models.flight import TrackedFlightStatus
from app.models.user import User
from app.services import rental_service
from app.services.settlement_service import LANDED_REASON, LOST_SIGNAL_REASON
from app.services.wallet_service import apply_ledger_entry, get_balance
from app.models.wallet import LedgerReason


async def _fund(db, user, amount=2000):
    await apply_ledger_entry(db, user.id, amount, LedgerReason.SIGNUP_BONUS)


async def test_create_rental_debits_wallet_and_creates_pending_rental(db, user, open_flight, item_type):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    assert rental.status == RentalStatus.PENDING
    assert await get_balance(db, user.id) == 1700


async def test_create_rental_display_code_starts_with_departure_time(
    db, user, open_flight, item_type
):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    expected_prefix = open_flight.first_seen_at.strftime("%Y%m%d-%H%M")
    assert rental.display_code.startswith(expected_prefix)
    # prefix + "-" + 5-char random suffix
    assert len(rental.display_code) == len(expected_prefix) + 1 + 5


async def test_two_rentals_on_same_flight_get_different_display_codes(
    db, user, open_flight, item_type
):
    await _fund(db, user, amount=4000)
    first = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    second = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    assert first.display_code != second.display_code
    # Same departure time -- same prefix.
    assert first.display_code.split("-")[:2] == second.display_code.split("-")[:2]


async def test_create_rental_insufficient_funds_raises(db, user, open_flight, item_type):
    await _fund(db, user, amount=100)
    with pytest.raises(InsufficientFundsError):
        await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)


async def test_create_rental_on_locked_flight_raises(db, user, open_flight, item_type):
    await _fund(db, user)
    open_flight.status = TrackedFlightStatus.AIRBORNE_LOCKED
    open_flight.capacity_open = False
    with pytest.raises(CapacityClosedError):
        await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)


async def test_create_rental_unknown_flight_raises(db, user, item_type):
    await _fund(db, user)
    with pytest.raises(NotFoundError):
        await rental_service.create_rental(db, user.id, 999, item_type.id, 300)


async def test_create_rental_unresolved_aircraft_type_raises(db, user, open_flight, item_type):
    await _fund(db, user)
    open_flight.aircraft_type_id = None
    with pytest.raises(LicenseRequiredError):
        await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)


async def test_create_rental_locked_aircraft_type_raises(
    db, user, open_flight, item_type, locked_aircraft_type
):
    await _fund(db, user)
    open_flight.aircraft_type_id = locked_aircraft_type.id
    with pytest.raises(LicenseRequiredError):
        await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)


async def test_create_rental_locked_airport_raises(
    db, user, open_flight, item_type, locked_airport
):
    await _fund(db, user)
    open_flight.origin_airport_id = locked_airport.id
    with pytest.raises(LicenseRequiredError):
        await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)


async def test_lock_capacity_transitions_pending_rentals_to_in_progress(db, user, open_flight, item_type):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)

    await rental_service.lock_capacity(db, open_flight)

    assert open_flight.status == TrackedFlightStatus.AIRBORNE_LOCKED
    assert open_flight.capacity_open is False
    refreshed = await rental_service.get_rental_for_user(db, user.id, rental.id)
    assert refreshed.status == RentalStatus.IN_PROGRESS


async def test_landing_suspected_then_rollback_returns_rental_to_in_progress(db, user, open_flight, item_type):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    await rental_service.lock_capacity(db, open_flight)

    now = datetime.now(timezone.utc)
    await rental_service.mark_landing_suspected(db, open_flight, now)
    refreshed = await rental_service.get_rental_for_user(db, user.id, rental.id)
    assert refreshed.status == RentalStatus.RESOLVING

    await rental_service.rollback_landing_suspected(db, open_flight)
    assert open_flight.status == TrackedFlightStatus.AIRBORNE_LOCKED
    refreshed = await rental_service.get_rental_for_user(db, user.id, rental.id)
    assert refreshed.status == RentalStatus.IN_PROGRESS


async def test_resolve_tracked_flight_computes_settlement_but_does_not_credit_wallet(
    db, user, open_flight, item_type
):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    await rental_service.lock_capacity(db, open_flight)
    balance_after_fee = await get_balance(db, user.id)

    resolved_at = open_flight.first_seen_at + timedelta(minutes=30)
    await rental_service.resolve_tracked_flight(
        db,
        open_flight,
        TrackedFlightStatus.RESOLVED_LANDED,
        LANDED_REASON,
        {"note": "test"},
        resolved_at=resolved_at,
    )

    refreshed = await rental_service.get_rental_for_user(db, user.id, rental.id)
    assert refreshed.status == RentalStatus.RESOLVED
    assert refreshed.settlement_credits == round(300 * 1.2 * 1.10)  # <60min bucket * item multiplier
    # Reward computed and stored, but NOT credited yet -- claim_rental() does that.
    assert await get_balance(db, user.id) == balance_after_fee


async def test_resolve_tracked_flight_fallback_pays_less_than_clean_landing(db, user, open_flight, item_type):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    await rental_service.lock_capacity(db, open_flight)

    resolved_at = open_flight.first_seen_at + timedelta(minutes=30)
    await rental_service.resolve_tracked_flight(
        db,
        open_flight,
        TrackedFlightStatus.RESOLVED_LOST_SIGNAL,
        LOST_SIGNAL_REASON,
        {"note": "vanished"},
        resolved_at=resolved_at,
    )

    refreshed = await rental_service.get_rental_for_user(db, user.id, rental.id)
    assert refreshed.resolution_reason == LOST_SIGNAL_REASON
    assert refreshed.settlement_credits < round(300 * 1.2 * 1.10)


async def test_claim_rental_credits_wallet_and_marks_claimed(db, user, open_flight, item_type):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    await rental_service.lock_capacity(db, open_flight)
    balance_before_claim = await get_balance(db, user.id)

    resolved_at = open_flight.first_seen_at + timedelta(minutes=30)
    await rental_service.resolve_tracked_flight(
        db, open_flight, TrackedFlightStatus.RESOLVED_LANDED, LANDED_REASON, {}, resolved_at=resolved_at
    )

    claimed = await rental_service.claim_rental(db, user.id, rental.id)

    assert claimed.status == RentalStatus.CLAIMED
    assert claimed.claimed_at is not None
    assert await get_balance(db, user.id) == balance_before_claim + claimed.settlement_credits


async def test_claim_rental_twice_raises_conflict(db, user, open_flight, item_type):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    await rental_service.lock_capacity(db, open_flight)
    resolved_at = open_flight.first_seen_at + timedelta(minutes=30)
    await rental_service.resolve_tracked_flight(
        db, open_flight, TrackedFlightStatus.RESOLVED_LANDED, LANDED_REASON, {}, resolved_at=resolved_at
    )
    await rental_service.claim_rental(db, user.id, rental.id)

    with pytest.raises(ConflictError):
        await rental_service.claim_rental(db, user.id, rental.id)


async def test_claim_rental_before_resolved_raises(db, user, open_flight, item_type):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)

    with pytest.raises(RentalNotResolvedError):
        await rental_service.claim_rental(db, user.id, rental.id)


async def test_claim_rental_for_other_users_rental_raises_not_found(
    db, user, open_flight, item_type
):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)

    other_user = User(email="other@example.com", password_hash="x", display_name="Other")
    db.add(other_user)
    await db.flush()

    with pytest.raises(NotFoundError):
        await rental_service.claim_rental(db, other_user.id, rental.id)
