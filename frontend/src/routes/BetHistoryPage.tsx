import { useQuery } from "@tanstack/react-query";
import { listMyBets } from "../api/bets";

export function BetHistoryPage() {
  const { data: bets, isLoading } = useQuery({
    queryKey: ["bets", "mine"],
    queryFn: () => listMyBets(),
    refetchInterval: 15000,
  });

  return (
    <div className="page">
      <h1>Bet History</h1>
      {isLoading && <p>Loading bets...</p>}
      {!isLoading && bets?.length === 0 && <p>No bets placed yet.</p>}

      <ul className="bet-list">
        {bets?.map((bet) => (
          <li key={bet.id} className="bet-card">
            <div>
              <strong>Bet #{bet.id}</strong>
              <span className={`bet-status bet-status-${bet.status.toLowerCase()}`}>
                {bet.status}
              </span>
            </div>
            <div>Stake: {bet.stake_credits} credits</div>
            {bet.status === "RESOLVED" && (
              <div>
                Payout: {bet.payout_credits} credits
                {bet.resolution_reason && ` (${bet.resolution_reason})`}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
