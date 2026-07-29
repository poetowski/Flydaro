from pydantic import BaseModel, ConfigDict


class ItemTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    category: str
    flavor_text: str
    settlement_multiplier: float
    base_cost_credits: int
