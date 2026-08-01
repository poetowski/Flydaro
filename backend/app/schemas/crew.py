from pydantic import BaseModel


class CrewOverviewEntryOut(BaseModel):
    airport_id: int
    icao4: str
    name: str
    crew_count: int
    busy_count: int
    free_count: int
    next_hire_cost: int
