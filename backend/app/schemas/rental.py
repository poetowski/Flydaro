from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateRentalRequest(BaseModel):
    tracked_flight_id: int
    item_type_id: int
    rental_fee_credits: int = Field(gt=0)


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
