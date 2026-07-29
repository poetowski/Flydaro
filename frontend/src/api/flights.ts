import { apiRequest } from "./client";

export interface TrackedFlight {
  id: number;
  icao24: string;
  callsign: string | null;
  origin_airport_id: number;
  aircraft_type_id: number | null;
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

export const getFlightBoard = (
  airportId?: number,
  aircraftTypeId?: number,
): Promise<TrackedFlight[]> => {
  const params = new URLSearchParams();
  if (airportId !== undefined) params.set("airport_id", String(airportId));
  if (aircraftTypeId !== undefined) params.set("aircraft_type_id", String(aircraftTypeId));
  const query = params.toString();
  return apiRequest<TrackedFlight[]>(`/flights/board${query ? `?${query}` : ""}`);
};

export const getFlight = (id: number): Promise<TrackedFlight> =>
  apiRequest<TrackedFlight>(`/flights/${id}`);
