import { apiRequest } from "./client";

export interface TrackedFlight {
  id: number;
  icao24: string;
  callsign: string | null;
  origin_airport_id: number;
  aircraft_type_id: number | null;
  status: string;
  capacity_open: boolean;
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
  aircraftFamilyId?: number,
): Promise<TrackedFlight[]> => {
  const params = new URLSearchParams();
  if (airportId !== undefined) params.set("airport_id", String(airportId));
  if (aircraftFamilyId !== undefined) params.set("aircraft_family_id", String(aircraftFamilyId));
  const query = params.toString();
  return apiRequest<TrackedFlight[]>(`/flights/board${query ? `?${query}` : ""}`);
};

export const getFlight = (id: number): Promise<TrackedFlight> =>
  apiRequest<TrackedFlight>(`/flights/${id}`);

export interface FlightSample {
  observed_at: string;
  lat: number | null;
  lon: number | null;
  baro_altitude: number | null;
  velocity: number | null;
  vertical_rate: number | null;
  on_ground: boolean | null;
}

export const getFlightSamples = (flightId: number): Promise<FlightSample[]> =>
  apiRequest<FlightSample[]>(`/flights/${flightId}/samples`);
