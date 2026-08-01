from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientFundsError
from app.models.rental import Rental
from app.models.wallet import LedgerReason, Wallet, WalletLedgerEntry


async def get_or_create_wallet(db: AsyncSession, user_id: int) -> Wallet:
    wallet = await db.get(Wallet, user_id)
    if wallet is None:
        wallet = Wallet(user_id=user_id, balance_credits=0)
        db.add(wallet)
        await db.flush()
    return wallet


async def apply_ledger_entry(
    db: AsyncSession,
    user_id: int,
    delta_credits: int,
    reason: LedgerReason,
    related_rental_id: int | None = None,
) -> Wallet:
    """Atomically apply a signed credit delta to a user's wallet via the ledger.

    The ledger row is the source of truth; `wallets.balance_credits` is a
    cached running total kept in sync here. Raises InsufficientFundsError
    rather than letting the balance go negative (enforced again by the DB
    CHECK constraint as a last line of defense).
    """
    wallet = await get_or_create_wallet(db, user_id)
    new_balance = wallet.balance_credits + delta_credits
    if new_balance < 0:
        raise InsufficientFundsError("Insufficient balance for this operation")

    wallet.balance_credits = new_balance
    db.add(
        WalletLedgerEntry(
            user_id=user_id,
            delta_credits=delta_credits,
            reason=reason,
            related_rental_id=related_rental_id,
        )
    )
    await db.flush()
    return wallet


async def get_balance(db: AsyncSession, user_id: int) -> int:
    wallet = await db.get(Wallet, user_id)
    return wallet.balance_credits if wallet else 0


async def list_ledger_entries(
    db: AsyncSession, user_id: int
) -> list[tuple[WalletLedgerEntry, str | None]]:
    """Each row pairs a ledger entry with its related rental's human-readable
    display_code (if any) -- one query, rather than N+1 lookups per entry,
    so the router can show "Rental fee -- 20260801-1423-7QXK" instead of a
    raw internal rental id."""
    result = await db.execute(
        select(WalletLedgerEntry, Rental.display_code)
        .outerjoin(Rental, Rental.id == WalletLedgerEntry.related_rental_id)
        .where(WalletLedgerEntry.user_id == user_id)
        # id as a tiebreaker: created_at alone isn't unique enough to order
        # by reliably -- func.now() has only second-level granularity on
        # SQLite (this suite's test DB), so two entries created in quick
        # succession can tie.
        .order_by(WalletLedgerEntry.created_at.desc(), WalletLedgerEntry.id.desc())
    )
    return list(result.all())
