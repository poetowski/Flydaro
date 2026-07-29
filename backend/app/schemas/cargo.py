from pydantic import BaseModel, ConfigDict


class CargoTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    flavor_text: str
    payout_multiplier: float
    base_cost_credits: int
