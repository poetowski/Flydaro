import { apiRequest } from "./client";

export interface ItemType {
  id: number;
  code: string;
  name: string;
  category: string;
  flavor_text: string;
  settlement_multiplier: number;
  base_cost_credits: number;
}

export const listItemTypes = (): Promise<ItemType[]> => apiRequest<ItemType[]>("/item-types");
