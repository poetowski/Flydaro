from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CargoType(Base):
    __tablename__ = "cargo_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    flavor_text: Mapped[str] = mapped_column(String(500), nullable=False)
    payout_multiplier: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    base_cost_credits: Mapped[int] = mapped_column(nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
