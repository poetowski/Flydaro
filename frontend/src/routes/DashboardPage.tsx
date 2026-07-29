import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listMyBets } from "../api/bets";
import { getWallet } from "../api/wallet";

const ACTIVE_STATUSES = new Set(["PENDING", "IN_PROGRESS", "RESOLVING"]);

export function DashboardPage() {
  const { data: wallet } = useQuery({ queryKey: ["wallet"], queryFn: getWallet });
  const { data: bets } = useQuery({ queryKey: ["bets", "mine"], queryFn: () => listMyBets() });

  const activeBets = bets?.filter((bet) => ACTIVE_STATUSES.has(bet.status)) ?? [];

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <section className="card">
        <h2>Wallet</h2>
        <p className="big-number">{wallet ? `${wallet.balance_credits} credits` : "Loading..."}</p>
      </section>

      <section className="card">
        <h2>Active bets ({activeBets.length})</h2>
        {activeBets.length === 0 ? (
          <p>
            No active bets right now. Head to the <Link to="/flights">flight board</Link> to place
            one.
          </p>
        ) : (
          <ul className="bet-list">
            {activeBets.map((bet) => (
              <li key={bet.id}>
                Bet #{bet.id} -- {bet.stake_credits} credits staked -- {bet.status}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
