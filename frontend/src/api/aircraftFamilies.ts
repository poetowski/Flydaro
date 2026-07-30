import { apiRequest } from "./client";

export interface AircraftFamilyMember {
  id: number;
  icao_type_code: string;
  name: string;
}

export interface AircraftFamily {
  id: number;
  code: string;
  name: string;
  unlock_cost_credits: number;
  unlocked: boolean;
  member_types: AircraftFamilyMember[];
}

export const listAircraftFamilies = (): Promise<AircraftFamily[]> =>
  apiRequest<AircraftFamily[]>("/aircraft-families");
