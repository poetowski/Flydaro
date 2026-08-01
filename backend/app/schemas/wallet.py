from datetime import datetime

from pydantic import BaseModel


class WalletOut(BaseModel):
    balance_credits: int


class WalletLedgerEntryOut(BaseModel):
    id: int
    delta_credits: int
    reason: str
    related_rental_id: int | None
    related_rental_code: str | None
    created_at: datetime
