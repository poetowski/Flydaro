import pytest

from app.core.exceptions import ConflictError
from app.services import license_service
from app.services.wallet_service import apply_ledger_entry, get_balance
from app.models.wallet import LedgerReason


async def _fund(db, user, amount=2000):
    await apply_ledger_entry(db, user.id, amount, LedgerReason.SIGNUP_BONUS)


async def test_unlock_airport_debits_wallet_and_flips_is_active(db, user, locked_airport):
    await _fund(db, user)
    airport = await license_service.unlock_airport(db, user.id, locked_airport.id)

    assert airport.is_active is True
    assert await get_balance(db, user.id) == 2000 - locked_airport.unlock_cost_credits
    assert await license_service.user_has_airport_unlock(db, user.id, airport) is True


async def test_unlock_airport_twice_conflicts_without_double_charge(db, user, locked_airport):
    await _fund(db, user)
    await license_service.unlock_airport(db, user.id, locked_airport.id)
    balance_after_first = await get_balance(db, user.id)

    with pytest.raises(ConflictError):
        await license_service.unlock_airport(db, user.id, locked_airport.id)

    assert await get_balance(db, user.id) == balance_after_first


async def test_unlock_starter_airport_conflicts(db, user, airport):
    await _fund(db, user)
    with pytest.raises(ConflictError):
        await license_service.unlock_airport(db, user.id, airport.id)


async def test_unlock_aircraft_type_debits_wallet(db, user, locked_aircraft_type):
    await _fund(db, user)
    aircraft_type = await license_service.unlock_aircraft_type(db, user.id, locked_aircraft_type.id)

    assert await get_balance(db, user.id) == 2000 - locked_aircraft_type.unlock_cost_credits
    assert (
        await license_service.user_has_aircraft_type_unlock(db, user.id, aircraft_type.id) is True
    )


async def test_get_unlocked_airport_ids_includes_starters_and_purchases(
    db, user, airport, locked_airport
):
    await _fund(db, user)
    unlocked_before = await license_service.get_unlocked_airport_ids(db, user.id)
    assert airport.id in unlocked_before
    assert locked_airport.id not in unlocked_before

    await license_service.unlock_airport(db, user.id, locked_airport.id)
    unlocked_after = await license_service.get_unlocked_airport_ids(db, user.id)
    assert locked_airport.id in unlocked_after
