import type { AircraftType } from "./aircraftTypes";
import type { Airport } from "./airports";
import { apiRequest } from "./client";

export const unlockAirport = (id: number): Promise<Airport> =>
  apiRequest<Airport>(`/licenses/airports/${id}/unlock`, { method: "POST" });

export const unlockAircraftType = (id: number): Promise<AircraftType> =>
  apiRequest<AircraftType>(`/licenses/aircraft-types/${id}/unlock`, { method: "POST" });
