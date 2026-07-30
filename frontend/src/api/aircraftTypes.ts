import { apiRequest } from "./client";

export interface AircraftType {
  id: number;
  icao_type_code: string;
  name: string;
  manufacturer: string;
  family_id: number | null;
}

export const listAircraftTypes = (): Promise<AircraftType[]> =>
  apiRequest<AircraftType[]>("/aircraft-types");
