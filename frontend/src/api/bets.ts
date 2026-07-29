import { apiRequest } from "./client";

export interface Bet {
  id: number;
  tracked_flight_id: number;
  cargo_type_id: number;
  stake_credits: number;
  status: string;
  placed_at: string;
  resolved_at: string | null;
  payout_credits: number | null;
  payout_breakdown: Record<string, unknown> | null;
  resolution_reason: string | null;
}

export const placeBet = (
  trackedFlightId: number,
  cargoTypeId: number,
  stakeCredits: number,
): Promise<Bet> =>
  apiRequest<Bet>("/bets", {
    method: "POST",
    body: {
      tracked_flight_id: trackedFlightId,
      cargo_type_id: cargoTypeId,
      stake_credits: stakeCredits,
    },
  });

export const listMyBets = (status?: string): Promise<Bet[]> =>
  apiRequest<Bet[]>(`/bets/mine${status ? `?status_filter=${status}` : ""}`);

export const getBet = (id: number): Promise<Bet> => apiRequest<Bet>(`/bets/${id}`);
