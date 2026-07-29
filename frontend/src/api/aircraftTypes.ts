import { apiRequest } from "./client";

export interface AircraftType {
  id: number;
  icao_type_code: string;
  name: string;
  manufacturer: string;
  unlock_cost_credits: number;
  unlocked: boolean;
}

export const listAircraftTypes = (): Promise<AircraftType[]> =>
  apiRequest<AircraftType[]>("/aircraft-types");
