import { apiRequest } from "./client";

export interface CargoType {
  id: number;
  code: string;
  name: string;
  flavor_text: string;
  payout_multiplier: number;
  base_cost_credits: number;
}

export const listCargoTypes = (): Promise<CargoType[]> => apiRequest<CargoType[]>("/cargo-types");
