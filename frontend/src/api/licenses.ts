import type { AircraftFamily } from "./aircraftFamilies";
import type { Airport } from "./airports";
import { apiRequest } from "./client";

export const unlockAirport = (id: number): Promise<Airport> =>
  apiRequest<Airport>(`/licenses/airports/${id}/unlock`, { method: "POST" });

export const unlockAircraftFamily = (id: number): Promise<AircraftFamily> =>
  apiRequest<AircraftFamily>(`/licenses/aircraft-families/${id}/unlock`, { method: "POST" });
