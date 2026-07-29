import pytest

from app.core.exceptions import InsufficientFundsError
from app.models.wallet import LedgerReason
from app.services.wallet_service import apply_ledger_entry, get_balance


async def test_credit_increases_balance(db, user):
    await apply_ledger_entry(db, user.id, 2000, LedgerReason.SIGNUP_BONUS)
    assert await get_balance(db, user.id) == 2000


async def test_debit_decreases_balance(db, user):
    await apply_ledger_entry(db, user.id, 2000, LedgerReason.SIGNUP_BONUS)
    await apply_ledger_entry(db, user.id, -500, LedgerReason.RENTAL_FEE)
    assert await get_balance(db, user.id) == 1500


async def test_debit_below_zero_raises_and_does_not_apply(db, user):
    await apply_ledger_entry(db, user.id, 100, LedgerReason.SIGNUP_BONUS)
    with pytest.raises(InsufficientFundsError):
        await apply_ledger_entry(db, user.id, -101, LedgerReason.RENTAL_FEE)
    # balance must be unchanged after the rejected debit
    assert await get_balance(db, user.id) == 100


async def test_balance_for_unknown_user_is_zero(db):
    assert await get_balance(db, 999) == 0
