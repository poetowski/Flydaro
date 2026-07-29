from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[int] = mapped_column(primary_key=True)
    icao4: Mapped[str] = mapped_column(String(4), unique=True, nullable=False, index=True)
    iata: Mapped[str | None] = mapped_column(String(3), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_lamin: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_lomin: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_lamax: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_lomax: Mapped[float] = mapped_column(Float, nullable=False)
    is_starter: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
