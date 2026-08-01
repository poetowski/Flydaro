import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.flight import JsonVariant


class RentalStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVING = "RESOLVING"
    RESOLVED = "RESOLVED"
    CLAIMED = "CLAIMED"


class Rental(Base):
    """A player renting a portion of a real aircraft's shared capacity to
    transport an item (see ItemType) on a specific tracked flight."""

    __tablename__ = "rentals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    tracked_flight_id: Mapped[int] = mapped_column(
        ForeignKey("tracked_flights.id"), nullable=False, index=True
    )
    item_type_id: Mapped[int] = mapped_column(ForeignKey("item_types.id"), nullable=False)
    # Human-readable name shown in the UI instead of the raw id -- the
    # tracked flight's departure time plus a random suffix (see
    # rental_service.generate_display_code), e.g. "20260801-1423-7QXK".
    display_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)

    rental_fee_credits: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[RentalStatus] = mapped_column(
        Enum(RentalStatus, name="rental_status", native_enum=False),
        nullable=False,
        default=RentalStatus.PENDING,
    )

    rented_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    settlement_credits: Mapped[int | None] = mapped_column(nullable=True)
    settlement_breakdown: Mapped[dict | None] = mapped_column(JsonVariant, nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(nullable=True)
