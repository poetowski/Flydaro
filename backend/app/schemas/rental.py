from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CreateRentalRequest(BaseModel):
    tracked_flight_id: int
    item_type_id: int
    rental_fee_credits: Literal[100, 250, 500, 1000]


class RentalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_code: str
    tracked_flight_id: int
    item_type_id: int
    rental_fee_credits: int
    status: str
    rented_at: datetime
    resolved_at: datetime | None
    settlement_credits: int | None
    settlement_breakdown: dict | None
    resolution_reason: str | None
    claimed_at: datetime | None
    # Populated by the router via rental_service.get_display_info_for_rentals
    # -- not present on the Rental ORM model itself, hence the default so
    # RentalOut.model_validate(rental) still succeeds before it's overlaid.
    origin_airport_code: str | None = None
    aircraft_family_code: str | None = None
