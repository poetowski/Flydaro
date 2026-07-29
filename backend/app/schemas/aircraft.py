from pydantic import BaseModel, ConfigDict


class AircraftTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    icao_type_code: str
    name: str
    manufacturer: str
    unlock_cost_credits: int
    unlocked: bool
