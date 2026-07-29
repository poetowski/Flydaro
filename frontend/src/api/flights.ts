import { apiRequest } from "./client";

export interface TrackedFlight {
  id: number;
  icao24: string;
  callsign: string | null;
  origin_airport_id: number;
  status: string;
  bets_open: boolean;
  first_seen_at: string;
  last_seen_at: string;
  last_seen_lat: number | null;
  last_seen_lon: number | null;
  last_seen_alt: number | null;
  resolved_at: string | null;
  resolution_summary: Record<string, unknown> | null;
}

export const getFlightBoard = (airportId?: number): Promise<TrackedFlight[]> =>
  apiRequest<TrackedFlight[]>(`/flights/board${airportId ? `?airport_id=${airportId}` : ""}`);

export const getFlight = (id: number): Promise<TrackedFlight> =>
  apiRequest<TrackedFlight>(`/flights/${id}`);
