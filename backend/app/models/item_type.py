import enum

from sqlalchemy import Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ItemCategory(str, enum.Enum):
    CARGO = "CARGO"
    PASSENGER = "PASSENGER"


class ItemType(Base):
    """Something a player can rent aircraft capacity to transport. Category
    is a top-level classification (Cargo vs Passenger); the specific items
    within each category and their characteristics are still being defined --
    the rows seeded today are placeholders recategorized from the earlier
    single-list "cargo type" model, not a final roster.
    """

    __tablename__ = "item_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[ItemCategory] = mapped_column(
        Enum(ItemCategory, name="item_category", native_enum=False), nullable=False
    )
    flavor_text: Mapped[str] = mapped_column(String(500), nullable=False)
    settlement_multiplier: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    base_cost_credits: Mapped[int] = mapped_column(nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
