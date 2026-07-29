from pydantic import BaseModel, ConfigDict


class AirportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    icao4: str
    iata: str | None
    name: str
    city: str
    country: str
