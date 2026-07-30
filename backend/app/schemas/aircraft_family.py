from pydantic import BaseModel


class AircraftFamilyMemberOut(BaseModel):
    id: int
    icao_type_code: str
    name: str


class AircraftFamilyOut(BaseModel):
    id: int
    code: str
    name: str
    unlock_cost_credits: int
    unlocked: bool
    member_types: list[AircraftFamilyMemberOut]
