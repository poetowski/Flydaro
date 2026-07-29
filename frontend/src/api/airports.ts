import { apiRequest } from "./client";

export interface Airport {
  id: number;
  icao4: string;
  iata: string | null;
  name: string;
  city: string;
  country: string;
}

export const listAirports = (): Promise<Airport[]> => apiRequest<Airport[]>("/airports");
