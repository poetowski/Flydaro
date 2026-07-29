from pydantic import BaseModel


class WalletOut(BaseModel):
    balance_credits: int
