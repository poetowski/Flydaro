import { apiRequest } from "./client";

export interface CrewOverviewEntry {
  airport_id: number;
  icao4: string;
  name: string;
  crew_count: number;
  busy_count: number;
  free_count: number;
  next_hire_cost: number;
}

export const getCrewOverview = (): Promise<CrewOverviewEntry[]> =>
  apiRequest<CrewOverviewEntry[]>("/crew");

export const hireCrew = (airportId: number): Promise<CrewOverviewEntry> =>
  apiRequest<CrewOverviewEntry>(`/crew/${airportId}/hire`, { method: "POST" });
