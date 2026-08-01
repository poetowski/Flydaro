import { apiRequest } from "./client";

export interface Rental {
  id: number;
  display_code: string;
  tracked_flight_id: number;
  item_type_id: number;
  rental_fee_credits: number;
  status: string;
  rented_at: string;
  resolved_at: string | null;
  settlement_credits: number | null;
  settlement_breakdown: Record<string, unknown> | null;
  resolution_reason: string | null;
  claimed_at: string | null;
  origin_airport_code: string | null;
  aircraft_family_code: string | null;
}

export const createRental = (
  trackedFlightId: number,
  itemTypeId: number,
  rentalFeeCredits: number,
): Promise<Rental> =>
  apiRequest<Rental>("/rentals", {
    method: "POST",
    body: {
      tracked_flight_id: trackedFlightId,
      item_type_id: itemTypeId,
      rental_fee_credits: rentalFeeCredits,
    },
  });

export const listMyRentals = (status?: string): Promise<Rental[]> =>
  apiRequest<Rental[]>(`/rentals/mine${status ? `?status_filter=${status}` : ""}`);

export const getRental = (id: number): Promise<Rental> => apiRequest<Rental>(`/rentals/${id}`);

export const claimRental = (id: number): Promise<Rental> =>
  apiRequest<Rental>(`/rentals/${id}/claim`, { method: "POST" });
