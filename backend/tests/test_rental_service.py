from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import (
    CapacityClosedError,
    InsufficientFundsError,
    LicenseRequiredError,
    NotFoundError,
)
from app.models.rental import RentalStatus
from app.models.flight import TrackedFlightStatus
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


async def test_resolve_tracked_flight_settles_and_credits_wallet(db, user, open_flight, item_type):
    await _fund(db, user)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    await rental_service.lock_capacity(db, open_flight)

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
    # balance = 2000 - 300 rental fee + settlement
    assert await get_balance(db, user.id) == 2000 - 300 + refreshed.settlement_credits


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
