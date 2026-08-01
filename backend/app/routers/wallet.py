from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.wallet import WalletLedgerEntryOut, WalletOut
from app.services.wallet_service import get_balance, list_ledger_entries

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/me", response_model=WalletOut)
async def get_my_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WalletOut:
    balance = await get_balance(db, current_user.id)
    return WalletOut(balance_credits=balance)


@router.get("/ledger", response_model=list[WalletLedgerEntryOut])
async def get_my_ledger(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WalletLedgerEntryOut]:
    entries = await list_ledger_entries(db, current_user.id)
    return [
        WalletLedgerEntryOut(
            id=entry.id,
            delta_credits=entry.delta_credits,
            reason=entry.reason.value,
            related_rental_id=entry.related_rental_id,
            related_rental_code=display_code,
            created_at=entry.created_at,
        )
        for entry, display_code in entries
    ]
