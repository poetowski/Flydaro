from datetime import timedelta

import pytest

from app.core.exceptions import LicenseRequiredError
from app.models.flight import TrackedFlightStatus
from app.models.rental import RentalStatus
from app.models.wallet import LedgerReason
from app.services import crew_service, license_service, rental_service
from app.services.wallet_service import apply_ledger_entry, get_balance


async def _fund(db, user, amount=2000):
    await apply_ledger_entry(db, user.id, amount, LedgerReason.SIGNUP_BONUS)


def test_hire_cost_scales_with_existing_crew():
    assert crew_service.hire_cost(0) == 600
    assert crew_service.hire_cost(1) == 1200
    assert crew_service.hire_cost(2) == 1800


async def test_hire_crew_debits_wallet_and_increments_count(db, user, airport):
    await _fund(db, user)
    balance_before = await get_balance(db, user.id)
    # Fixture already grants 1 crew member at `airport` -- next hire costs hire_cost(1).
    expected_cost = crew_service.hire_cost(1)

    crew = await crew_service.hire_crew(db, user.id, airport.id)

    assert crew.crew_count == 2
    assert await get_balance(db, user.id) == balance_before - expected_cost


async def test_hire_crew_on_locked_airport_raises(db, user, locked_airport):
    await _fund(db, user)
    with pytest.raises(LicenseRequiredError):
        await crew_service.hire_crew(db, user.id, locked_airport.id)


async def test_get_crew_overview_includes_unlocked_never_hired_airport(db, user, locked_airport):
    """An unlocked airport with zero crew hires should still appear as
    0/0/0, not be silently omitted -- but this fixture's `airport` (the
    only unlocked one available here) already has 1 crew from its own
    fixture setup, so unlock `locked_airport` with no crew hire and
    confirm it shows up as 0/0."""
    await _fund(db, user, amount=2000)
    await license_service.unlock_airport(db, user.id, locked_airport.id)

    overview = await crew_service.get_crew_overview(db, user.id)
    _, crew_count, busy_count = next(row for row in overview if row[0].id == locked_airport.id)
    assert crew_count == 0
    assert busy_count == 0


async def test_count_busy_rentals_only_counts_non_resolved(db, user, airport, open_flight, item_type):
    await _fund(db, user, amount=2000)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)
    assert await crew_service.count_busy_rentals(db, user.id, airport.id) == 1

    resolved_at = open_flight.first_seen_at + timedelta(minutes=30)
    await rental_service.resolve_tracked_flight(
        db,
        open_flight,
        TrackedFlightStatus.RESOLVED_LANDED,
        "landed",
        {},
        resolved_at=resolved_at,
    )
    assert rental.status == RentalStatus.RESOLVED
    assert await crew_service.count_busy_rentals(db, user.id, airport.id) == 0
