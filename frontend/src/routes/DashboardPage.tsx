import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listMyRentals } from "../api/rentals";
import { getWallet } from "../api/wallet";

const ACTIVE_STATUSES = new Set(["PENDING", "IN_PROGRESS", "RESOLVING"]);

export function DashboardPage() {
  const { data: wallet } = useQuery({ queryKey: ["wallet"], queryFn: getWallet });
  const { data: rentals } = useQuery({ queryKey: ["rentals", "mine"], queryFn: () => listMyRentals() });

  const activeRentals = rentals?.filter((rental) => ACTIVE_STATUSES.has(rental.status)) ?? [];

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <section className="card">
        <h2>Wallet</h2>
        <p className="big-number">{wallet ? `${wallet.balance_credits} credits` : "Loading..."}</p>
      </section>

      <section className="card">
        <h2>Active rentals ({activeRentals.length})</h2>
        {activeRentals.length === 0 ? (
          <p>
            No active rentals right now. Head to the <Link to="/flights">flight board</Link> to
            rent some capacity.
          </p>
        ) : (
          <ul className="rental-list">
            {activeRentals.map((rental) => (
              <li key={rental.id}>
                {rental.display_code} -- {rental.rental_fee_credits} credits -- {rental.status}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
