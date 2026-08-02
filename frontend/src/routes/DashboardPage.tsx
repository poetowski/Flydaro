import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listAircraftFamilies } from "../api/aircraftFamilies";
import { listAirports } from "../api/airports";
import { getCurrentUser } from "../api/auth";
import { getCrewOverview } from "../api/crew";
import { getMyRank } from "../api/leaderboard";
import { listMyRentals } from "../api/rentals";
import { getWallet, getWalletLedger } from "../api/wallet";
import { CreditsChart, type CreditsChartPoint } from "../components/CreditsChart";
import { useLanguage, dateLocale } from "../i18n";
import { translateApiError } from "../i18n/translateApiError";
import { useReasonLabel } from "../lib/ledgerLabels";
import { familyBadgeLabel } from "../lib/familyLabel";

const ACTIVE_STATUSES = new Set(["FLYING", "IN_PROGRESS", "RESOLVING"]);
const RECENT_ACTIVITY_COUNT = 5;

export function DashboardPage() {
  const { t, tPlural, language } = useLanguage();
  const reasonLabel = useReasonLabel();
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
    ? new Date(currentUser.created_at).toLocaleDateString(dateLocale(language), {
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <div className="page">
      <h1>{t("dashboard.title")}</h1>
      <p className="muted">
        {currentUser ? t("dashboard.welcomeBackNamed", { name: currentUser.display_name }) : t("dashboard.welcomeBack")}
        {memberSince ? t("dashboard.memberSince", { date: memberSince }) : ""}
        {myRank
          ? t("dashboard.rankedSuffix", {
              rank: myRank.rank,
              total: myRank.total_players,
              bracket: myRank.credit_bracket,
            })
          : ""}
      </p>

      <section className="card">
        <h2>{t("dashboard.walletHeading")}</h2>
        <p className="big-number">
          {wallet ? t("common.creditsAmount", { amount: wallet.balance_credits }) : t("dashboard.walletLoading")}
        </p>
      </section>

      <section className="card">
        <h2>{t("dashboard.creditsOverTimeHeading")}</h2>
        {ledgerIsError ? (
          <p className="form-error">
            {t("dashboard.couldNotLoadCreditHistory", { error: translateApiError(ledgerError, t) })}
          </p>
        ) : (
          <CreditsChart
            points={chartPoints}
            language={language}
            emptyLabel={t("charts.creditsChartEmpty")}
            ariaLabel={t("charts.creditsChartLabel")}
          />
        )}
      </section>

      <section className="card stat-row">
        <div className="stat-card">
          <p className="stat-value">{activeRentals.length}</p>
          <p className="stat-label">{t("dashboard.activeRentalsLabel")}</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{unclaimedTotal}</p>
          <p className="stat-label">{t("dashboard.unclaimedRewardsLabel")}</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{lifetimeClaimed}</p>
          <p className="stat-label">{t("dashboard.lifetimeClaimedLabel")}</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">{idleCrew}</p>
          <p className="stat-label">{t("dashboard.idleCrewLabel")}</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">
            {airportsUnlockedCount}/{airports?.length ?? "-"}
          </p>
          <p className="stat-label">{t("dashboard.airportsUnlockedLabel")}</p>
        </div>
        <div className="stat-card">
          <p className="stat-value">
            {familiesUnlockedCount}/{aircraftFamilies?.length ?? "-"}
          </p>
          <p className="stat-label">{t("dashboard.familiesUnlockedLabel")}</p>
        </div>
      </section>
      {(crewIsError || airportsIsError || aircraftFamiliesIsError) && (
        <p className="form-error">
          {t("dashboard.someStatsCouldNotLoad", {
            error: translateApiError(crewError ?? airportsError ?? aircraftFamiliesError, t),
          })}
        </p>
      )}

      {unclaimedRentals.length > 0 && (
        <section className="card card-highlight">
          <p>{tPlural("dashboard.unclaimedRewards", unclaimedRentals.length, { total: unclaimedTotal })}</p>
          <Link className="button" to="/rentals">
            {t("dashboard.goClaimThem")}
          </Link>
        </section>
      )}

      <section className="card">
        <h2>{t("dashboard.activeRentalsHeading", { count: activeRentals.length })}</h2>
        {rentalsIsError && (
          <p className="form-error">
            {t("dashboard.couldNotLoadRentals", { error: translateApiError(rentalsError, t) })}
          </p>
        )}
        {activeRentals.length === 0 ? (
          <p>
            {t("dashboard.noActiveRentalsPre")}
            <Link to="/flights">{t("nav.flightBoard")}</Link>
            {t("dashboard.noActiveRentalsPost")}
          </p>
        ) : (
          <ul className="rental-list">
            {activeRentals.map((rental) => (
              <li key={rental.id} className="rental-card">
                <div>
                  <strong>{rental.display_code}</strong>
                  <span className={`rental-status rental-status-${rental.status.toLowerCase()}`}>
                    {t(`rentalStatusBadge.${rental.status}`)}
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
                <div>{t("dashboard.rentalFeeLine", { amount: rental.rental_fee_credits })}</div>
              </li>
            ))}
          </ul>
        )}
        <Link to="/rentals">{t("dashboard.viewAllRentals")}</Link>
      </section>

      <section className="card">
        <h2>{t("dashboard.recentActivityHeading")}</h2>
        {ledgerIsError && (
          <p className="form-error">
            {t("dashboard.couldNotLoadActivity", { error: translateApiError(ledgerError, t) })}
          </p>
        )}
        {recentActivity.length === 0 && !ledgerIsError && <p>{t("dashboard.noActivityYet")}</p>}
        <ul className="ledger-list">
          {recentActivity.map((entry) => (
            <li key={entry.id} className="ledger-entry">
              <div>
                <strong>{reasonLabel(entry.reason)}</strong>
                {entry.related_rental_code && (
                  <span className="flight-meta"> -- {entry.related_rental_code}</span>
                )}
              </div>
              <div className="flight-meta">
                {new Date(entry.created_at).toLocaleString(dateLocale(language))}
              </div>
              <div className={entry.delta_credits >= 0 ? "ledger-amount-positive" : "ledger-amount-negative"}>
                {entry.delta_credits >= 0 ? "+" : ""}
                {t("common.creditsAmount", { amount: entry.delta_credits })}
              </div>
            </li>
          ))}
        </ul>
        <Link to="/wallet-ledger">{t("dashboard.viewFullLedger")}</Link>
      </section>

      <section className="card stat-row">
        <Link className="button" to="/flights">
          {t("dashboard.rentCapacity")}
        </Link>
        <Link className="button" to="/the-crew">
          {t("dashboard.hireCrew")}
        </Link>
        <Link className="button" to="/licenses">
          {t("dashboard.unlockLicenses")}
        </Link>
        <Link className="button" to="/board-of-fame">
          {t("nav.boardOfFame")}
        </Link>
      </section>
    </div>
  );
}
