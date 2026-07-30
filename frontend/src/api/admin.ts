import { apiRequest } from "./client";

export interface PollerHeartbeat {
  last_tick_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
  credits_remaining: number | null;
  seconds_since_last_tick: number | null;
  expected_interval_seconds: number;
}

export interface FlightStatusCount {
  status: string;
  count: number;
}

export interface RecentFlight {
  id: number;
  icao24: string;
  callsign: string | null;
  origin_airport_name: string;
  aircraft_type_name: string | null;
  status: string;
  first_seen_at: string;
}

export interface ActiveAirport {
  id: number;
  icao4: string;
  name: string;
}

export interface PollerHealth {
  heartbeat: PollerHeartbeat;
  status_counts: FlightStatusCount[];
  recent_flights: RecentFlight[];
  active_airports: ActiveAirport[];
}

export const getPollerHealth = (): Promise<PollerHealth> =>
  apiRequest<PollerHealth>("/admin/poller-health");
