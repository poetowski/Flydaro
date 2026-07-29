from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserAirportUnlock(Base):
    __tablename__ = "user_airport_unlocks"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), primary_key=True)
    unlocked_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class UserAircraftTypeUnlock(Base):
    __tablename__ = "user_aircraft_type_unlocks"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    aircraft_type_id: Mapped[int] = mapped_column(
        ForeignKey("aircraft_types.id"), primary_key=True
    )
    unlocked_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
