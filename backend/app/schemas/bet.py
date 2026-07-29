from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlaceBetRequest(BaseModel):
    tracked_flight_id: int
    cargo_type_id: int
    stake_credits: int = Field(gt=0)


class BetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tracked_flight_id: int
    cargo_type_id: int
    stake_credits: int
    status: str
    placed_at: datetime
    resolved_at: datetime | None
    payout_credits: int | None
    payout_breakdown: dict | None
    resolution_reason: str | None
