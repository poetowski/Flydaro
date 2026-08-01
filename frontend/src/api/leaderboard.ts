import { apiRequest } from "./client";

export interface LeaderboardEntry {
  rank: number;
  display_name: string;
  credit_bracket: string;
}

export const getLeaderboard = (): Promise<LeaderboardEntry[]> =>
  apiRequest<LeaderboardEntry[]>("/leaderboard");
