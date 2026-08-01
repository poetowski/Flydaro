from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserAirportCrew(Base):
    """How many crew members a player has hired at a given airport --
    a crew member is permanently tied to the airport they were hired at
    (never transferable). This is the ceiling on how many of that user's
    rentals originating from this airport can be in progress at once;
    how many are currently *busy* is derived on the fly from `rentals`/
    `tracked_flights` (see app/services/crew_service.py), not stored here.
    """

    __tablename__ = "user_airport_crew"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), primary_key=True)
    crew_count: Mapped[int] = mapped_column(nullable=False, default=0)
