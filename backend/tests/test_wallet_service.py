import pytest

from app.core.exceptions import InsufficientFundsError
from app.models.user import User
from app.models.wallet import LedgerReason
from app.services.wallet_service import apply_ledger_entry, get_balance, list_ledger_entries


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


async def test_list_ledger_entries_newest_first(db, user):
    await apply_ledger_entry(db, user.id, 2000, LedgerReason.SIGNUP_BONUS)
    await apply_ledger_entry(db, user.id, -500, LedgerReason.RENTAL_FEE)

    entries = await list_ledger_entries(db, user.id)

    assert [entry.reason for entry, _ in entries] == [
        LedgerReason.RENTAL_FEE,
        LedgerReason.SIGNUP_BONUS,
    ]
    assert [entry.delta_credits for entry, _ in entries] == [-500, 2000]


async def test_list_ledger_entries_scoped_to_requesting_user(db, user):
    other_user = User(email="other@example.com", password_hash="x", display_name="Other")
    db.add(other_user)
    await db.flush()

    await apply_ledger_entry(db, user.id, 2000, LedgerReason.SIGNUP_BONUS)
    await apply_ledger_entry(db, other_user.id, 2000, LedgerReason.SIGNUP_BONUS)

    entries = await list_ledger_entries(db, user.id)
    assert len(entries) == 1


async def test_list_ledger_entries_includes_related_rental_display_code(
    db, user, open_flight, item_type
):
    from app.services import rental_service

    await apply_ledger_entry(db, user.id, 2000, LedgerReason.SIGNUP_BONUS)
    rental = await rental_service.create_rental(db, user.id, open_flight.id, item_type.id, 300)

    entries = await list_ledger_entries(db, user.id)
    fee_entry, display_code = next(
        (entry, code) for entry, code in entries if entry.reason == LedgerReason.RENTAL_FEE
    )
    assert fee_entry.related_rental_id == rental.id
    assert display_code == rental.display_code
