from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientFundsError
from app.models.rental import Rental
from app.models.user import User
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


def credit_bracket(balance_credits: int) -> str:
    """Magnitude bracket for the leaderboard -- deliberately never exposes
    the exact balance, only which order-of-magnitude bucket it falls in."""
    if balance_credits < 1_000:
        return "0-1k"
    if balance_credits < 10_000:
        return "1-10k"
    if balance_credits < 100_000:
        return "10-100k"
    return "100k+"


async def get_user_rank(db: AsyncSession, user_id: int) -> tuple[int, int]:
    """(rank, total_players) for the requesting user's own standing --
    private to them, reveals nothing about any other specific user's
    balance (same property the public leaderboard's bracket system
    already has). Rank is 1 + how many players have a strictly greater
    balance; ties share the same rank rather than being arbitrarily
    broken."""
    balance = await get_balance(db, user_id)
    higher_count = await db.scalar(
        select(func.count()).select_from(Wallet).where(Wallet.balance_credits > balance)
    )
    total = await db.scalar(select(func.count()).select_from(User))
    return (higher_count or 0) + 1, total or 0


async def get_leaderboard(db: AsyncSession, limit: int = 10) -> list[tuple[str, int]]:
    """Top-N (display_name, balance_credits) pairs, highest balance first.
    A LEFT JOIN (not inner) so a user without a wallet row yet still shows
    up with a 0 balance rather than being silently dropped -- shouldn't
    happen in practice (signup always credits a signup bonus, creating the
    wallet row), but the correct join shape regardless. User.id is a
    tiebreaker for deterministic ordering across equal balances."""
    result = await db.execute(
        select(User.display_name, func.coalesce(Wallet.balance_credits, 0))
        .outerjoin(Wallet, Wallet.user_id == User.id)
        .order_by(func.coalesce(Wallet.balance_credits, 0).desc(), User.id.asc())
        .limit(limit)
    )
    return list(result.all())
