from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PollerHeartbeatOut(BaseModel):
    last_tick_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    credits_remaining: int | None
    last_opensky_status: int | None
    last_opensky_detail: str | None
    seconds_since_last_tick: float | None
    # Exposed rather than hardcoded on the frontend, so the staleness
    # threshold there always tracks the actually-configured interval
    # instead of drifting if poller_interval_seconds ever changes in prod.
    expected_interval_seconds: int


class FlightStatusCountOut(BaseModel):
    status: str
    count: int


class RecentFlightOut(BaseModel):
    id: int
    icao24: str
    callsign: str | None
    origin_airport_name: str
    aircraft_type_name: str | None
    status: str
    first_seen_at: datetime


class ActiveAirportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    icao4: str
    name: str


class PollerHealthOut(BaseModel):
    heartbeat: PollerHeartbeatOut
    status_counts: list[FlightStatusCountOut]
    recent_flights: list[RecentFlightOut]
    active_airports: list[ActiveAirportOut]
