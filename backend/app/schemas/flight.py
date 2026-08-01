from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrackedFlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    icao24: str
    callsign: str | None
    origin_airport_id: int
    aircraft_type_id: int | None
    status: str
    capacity_open: bool
    first_seen_at: datetime
    last_seen_at: datetime
    last_seen_lat: float | None
    last_seen_lon: float | None
    last_seen_alt: float | None
    resolved_at: datetime | None
    resolution_summary: dict | None


class FlightStateSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    observed_at: datetime
    lat: float | None
    lon: float | None
    baro_altitude: float | None
    velocity: float | None
    vertical_rate: float | None
    on_ground: bool | None
