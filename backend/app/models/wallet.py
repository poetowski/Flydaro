import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LedgerReason(str, enum.Enum):
    SIGNUP_BONUS = "signup_bonus"
    BET_STAKE = "bet_stake"
    BET_PAYOUT = "bet_payout"
    LICENSE_PURCHASE = "license_purchase"
    CARGO_PURCHASE = "cargo_purchase"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (CheckConstraint("balance_credits >= 0", name="ck_wallet_balance_nonneg"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    balance_credits: Mapped[int] = mapped_column(nullable=False, default=0)


class WalletLedgerEntry(Base):
    __tablename__ = "wallet_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    delta_credits: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[LedgerReason] = mapped_column(
        Enum(
            LedgerReason,
            name="ledger_reason",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    related_bet_id: Mapped[int | None] = mapped_column(ForeignKey("bets.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
