import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.flight import JsonVariant


class BetStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVING = "RESOLVING"
    RESOLVED = "RESOLVED"


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    tracked_flight_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_flights.id"), nullable=False, index=True
    )
    cargo_type_id: Mapped[int] = mapped_column(ForeignKey("cargo_types.id"), nullable=False)

    stake_credits: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[BetStatus] = mapped_column(
        Enum(BetStatus, name="bet_status", native_enum=False),
        nullable=False,
        default=BetStatus.PENDING,
    )

    placed_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    payout_credits: Mapped[int | None] = mapped_column(nullable=True)
    payout_breakdown: Mapped[dict | None] = mapped_column(JsonVariant, nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
