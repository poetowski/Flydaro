import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listAircraftFamilies } from "../api/aircraftFamilies";
import { listAirports } from "../api/airports";
import { getCurrentUser } from "../api/auth";
import { ApiError } from "../api/client";
import { getCrewOverview } from "../api/crew";
import { getMyRank } from "../api/leaderboard";
import { listMyRentals } from "../api/rentals";
import { getWallet, getWalletLedger } from "../api/wallet";
import { CreditsChart, type CreditsChartPoint } from "../components/CreditsChart";
import { REASON_LABELS } from "../lib/ledgerLabels";
import { familyBadgeLabel } from "../lib/familyLabel";

const ACTIVE_STATUSES = new Set(["FLYING", "IN_PROGRESS", "RESOLVING"]);
const RECENT_ACTIVITY_COUNT = 5;

function queryErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function DashboardPage() {
  const { data: wallet } = useQuery({ queryKey: ["wallet"], queryFn: getWallet });
  const {
    data: rentals,
    isError: rentalsIsError,
    error: rentalsError,
  } = useQuery({ queryKey: ["rentals", "mine"], queryFn: () => listMyRentals() });
  const {
    data: ledger,
    isError: ledgerIsError,
    error: ledgerError,
  } = useQuery({ queryKey: ["wallet", "ledger"], queryFn: getWalletLedger });
  const {
    data: crewOverview,
    isError: crewIsError,
    error: crewError,
  } = useQuery({ queryKey: ["crew"], queryFn: getCrewOverview });
  const {
    data: airports,
    isError: airportsIsError,
    error: airportsError,
  } = useQuery({ queryKey: ["airports"], queryFn: listAirports });
  const {
    data: aircraftFamilies,
    isError: aircraftFamiliesIsError,
    error: aircraftFamiliesError,
  } = useQuery({ queryKey: ["aircraft-families"], queryFn: listAircraftFamilies });
  const { data: currentUser } = useQuery({ queryKey: ["me"], queryFn: getCurrentUser });
  const { data: myRank } = useQuery({ queryKey: ["leaderboard", "me"], queryFn: getMyRank });

  const activeRentals = rentals?.filter((rental) => ACTIVE_STATUSES.has(rental.status)) ?? [];
  const unclaimedRentals = rentals?.filter((rental) => rental.status === "RESOLVED") ?? [];
  const unclaimedTotal = unclaimedRentals.reduce(
    (sum, rental) => sum + (rental.settlement_credits ?? 0),
    0,
  );
  const lifetimeClaimed = (rentals ?? [])
    .filter((rental) => rental.status === "CLAIMED")
    .reduce((sum, rental) => sum + (rental.settlement_credits ?? 0), 0);

  const totalCrew = (crewOverview ?? []).reduce((sum, c) => sum + c.crew_count, 0);
  const busyCrew = (crewOverview ?? []).reduce((sum, c) => sum + c.busy_count, 0);
  const idleCrew = totalCrew - busyCrew;

  const airportsUnlockedCount = (airports ?? []).filter((a) => a.unlocked).length;
  const familiesUnlockedCount = (aircraftFamilies ?? []).filter((f) => f.unlocked).length;

  // Ledger arrives newest-first; reverse to chronological order and run a
  // cumulative sum so each point is the real balance at that real moment.
  let chartPoints: CreditsChartPoint[] = [];
  if (ledger && ledger.length > 0) {
    const chronological = [...ledger].reverse();
    let running = 0;
    chartPoints = chronological.map((entry) => {
      running += entry.delta_credits;
      return { date: new Date(entry.created_at), balance: running };
    });
  }

  const recentActivity = (ledger ?? []).slice(0, RECENT_ACTIVITY_COUNT);

  const memberSince = currentUser
    ? new Date(currentUser.created_at).toLocaleDateString(undefined, {
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <div className="page">
      <h1>Dashboard</h1>
      <p className="muted">
        {currentUser ? `Welcome back, ${currentUser.display_name}` : "Welcome back"}
        {memberSince ? ` -- member since ${memberSince}` : ""}
        {myRank ? ` -- Ranked #${myRank.rank} of ${myRank.total_players} (${myRank.credit_bracket})` : ""}
      </p>

      <section className="card">
        <h2>Wallet</h2>
        <p className="big-number">{wallet ? `${wallet.balance_credits} credits` : "Loading..."}</p>
      </section>

      <section className="card">
        <h2>Credits Over Time</h2>
        {ledgerIsError ? (
          <p className="form-error">
            Could not load your credit history: {queryErrorMessage(ledgerError, "unknown error")}
          </p>
        ) : (
          <CreditsChart points={chartPoints} />
        )}
      </section>

      <section className="card stat-row">
        <div className="stat-card">
          <p className="stat-value">{activeRentals.length}</p>
          <p className="stat-label">Active Rentals</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{unclaimedTotal}</p>
          <p className="stat-label">Unclaimed Rewards (credits)</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{lifetimeClaimed}</p>
          <p className="stat-label">Lifetime Claimed (credits)</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{idleCrew}</p>
          <p className="stat-label">Idle Crew</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">
            {airportsUnlockedCount}/{airports?.length ?? "-"}
          </p>
          <p className="stat-label">Airports Unlocked</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">
            {familiesUnlockedCount}/{aircraftFamilies?.length ?? "-"}
          </p>
          <p className="stat-label">Aircraft Families Unlocked</p>
        </div>
      </section>
      {(crewIsError || airportsIsError || aircraftFamiliesIsError) && (
        <p className="form-error">
          Some stats could not load:{" "}
          {queryErrorMessage(crewError ?? airportsError ?? aircraftFamiliesError, "unknown error")}
        </p>
      )}

      {unclaimedRentals.length > 0 && (
        <section className="card card-highlight">
          <p>
            You have {unclaimedRentals.length} unclaimed reward{unclaimedRentals.length === 1 ? "" : "s"}{" "}
            worth {unclaimedTotal} credits waiting.
          </p>
          <Link className="button" to="/rentals">
            Go claim them
          </Link>
        </section>
      )}

      <section className="card">
        <h2>Active rentals ({activeRentals.length})</h2>
        {rentalsIsError && (
          <p className="form-error">
            Could not load rentals: {queryErrorMessage(rentalsError, "unknown error")}
          </p>
        )}
        {activeRentals.length === 0 ? (
          <p>
            No active rentals right now. Head to the <Link to="/flights">flight board</Link> to
            rent some capacity.
          </p>
        ) : (
          <ul className="rental-list">
            {activeRentals.map((rental) => (
              <li key={rental.id} className="rental-card">
                <div>
                  <strong>{rental.display_code}</strong>
                  <span className={`rental-status rental-status-${rental.status.toLowerCase()}`}>
                    {rental.status}
                  </span>
                </div>
                <div>
                  {rental.origin_airport_code && (
                    <span className="badge badge-airport">{rental.origin_airport_code}</span>
                  )}
                  {rental.aircraft_family_code && (
                    <span className="badge badge-family" style={{ marginLeft: 6 }}>
                      {familyBadgeLabel(rental.aircraft_family_code)}
                    </span>
                  )}
                </div>
                <div>Rental fee: {rental.rental_fee_credits} credits</div>
              </li>
            ))}
          </ul>
        )}
        <Link to="/rentals">View all rentals</Link>
      </section>

      <section className="card">
        <h2>Recent activity</h2>
        {ledgerIsError && (
          <p className="form-error">
            Could not load activity: {queryErrorMessage(ledgerError, "unknown error")}
          </p>
        )}
        {recentActivity.length === 0 && !ledgerIsError && <p>No activity yet.</p>}
        <ul className="ledger-list">
          {recentActivity.map((entry) => (
            <li key={entry.id} className="ledger-entry">
              <div>
                <strong>{REASON_LABELS[entry.reason] ?? entry.reason}</strong>
                {entry.related_rental_code && (
                  <span className="flight-meta"> -- {entry.related_rental_code}</span>
                )}
              </div>
              <div className="flight-meta">{new Date(entry.created_at).toLocaleString()}</div>
              <div className={entry.delta_credits >= 0 ? "ledger-amount-positive" : "ledger-amount-negative"}>
                {entry.delta_credits >= 0 ? "+" : ""}
                {entry.delta_credits} credits
              </div>
            </li>
          ))}
        </ul>
        <Link to="/wallet-ledger">View full ledger</Link>
      </section>

      <section className="card stat-row">
        <Link className="button" to="/flights">
          Rent Capacity
        </Link>
        <Link className="button" to="/the-crew">
          Hire Crew
        </Link>
        <Link className="button" to="/licenses">
          Unlock Licenses
        </Link>
        <Link className="button" to="/board-of-fame">
          Board of Fame
        </Link>
      </section>
    </div>
  );
}
