import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
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
import { ACHIEVEMENTS, type AchievementData } from "../lib/achievements";
import { useReasonLabel } from "../lib/ledgerLabels";
import { familyBadgeLabel } from "../lib/familyLabel";
import { PAGE_ICONS } from "../lib/pageIcons";
import { getSeenAchievements, markSeen } from "../lib/seenAchievements";
import { RENTAL_STATUS_ICONS } from "../lib/statusIcons";
import { useToast } from "../lib/ToastContext";

const ACHIEVEMENT_POP_DURATION_MS = 500;

const ACTIVE_STATUSES = new Set(["FLYING", "IN_PROGRESS", "RESOLVING"]);
const RECENT_ACTIVITY_COUNT = 5;

export function DashboardPage() {
  const { t, tPlural, language } = useLanguage();
  const { showToast } = useToast();
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

  // Next Goal: cheapest currently-locked airport/family, if any remain.
  const cheapestLockedAirport = (airports ?? [])
    .filter((a) => !a.unlocked)
    .sort((a, b) => a.unlock_cost_credits - b.unlock_cost_credits)[0];
  const cheapestLockedFamily = (aircraftFamilies ?? [])
    .filter((f) => !f.unlocked)
    .sort((a, b) => a.unlock_cost_credits - b.unlock_cost_credits)[0];
  const balance = wallet?.balance_credits ?? 0;

  const achievementData: AchievementData = {
    rentals: rentals ?? [],
    ledger: ledger ?? [],
    wallet,
    airports: airports ?? [],
    aircraftFamilies: aircraftFamilies ?? [],
    crewOverview: crewOverview ?? [],
    myRank,
  };
  const earnedIds = ACHIEVEMENTS.filter((a) => a.computeEarned(achievementData)).map((a) => a.id);
  const earnedIdsKey = earnedIds.join(",");
  const [poppingIds, setPoppingIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (earnedIds.length === 0) return;
    const seen = getSeenAchievements();
    const newlyEarned = earnedIds.filter((id) => !seen.has(id));
    if (newlyEarned.length === 0) return;
    newlyEarned.forEach((id) => {
      showToast(t("dashboard.achievementUnlockedToast", { title: t(`achievements.${id}.title`) }));
    });
    markSeen(newlyEarned);
    setPoppingIds(new Set(newlyEarned));
    const timeoutId = setTimeout(() => setPoppingIds(new Set()), ACHIEVEMENT_POP_DURATION_MS);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [earnedIdsKey]);

  return (
    <div className="page">
      <h1>
        {PAGE_ICONS["/"]} {t("dashboard.title")}
      </h1>
      <div className="dashboard-hero">
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
        <p className="big-number">
          {wallet ? t("common.creditsAmount", { amount: wallet.balance_credits }) : t("dashboard.walletLoading")}
        </p>
      </div>

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

      <section className="card">
        <h2>{t("dashboard.nextGoalHeading")}</h2>
        {!cheapestLockedAirport && !cheapestLockedFamily ? (
          <p>{t("dashboard.nextGoalAllUnlocked")}</p>
        ) : (
          <>
            {cheapestLockedAirport && (
              <div style={{ marginBottom: 12 }}>
                <p className="flight-meta">
                  {t("dashboard.nextGoalAirport", {
                    name: cheapestLockedAirport.name,
                    balance: Math.min(balance, cheapestLockedAirport.unlock_cost_credits),
                    cost: cheapestLockedAirport.unlock_cost_credits,
                  })}
                </p>
                <div className="progress-bar">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${Math.min(100, (balance / cheapestLockedAirport.unlock_cost_credits) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            )}
            {cheapestLockedFamily && (
              <div>
                <p className="flight-meta">
                  {t("dashboard.nextGoalFamily", {
                    name: cheapestLockedFamily.name,
                    balance: Math.min(balance, cheapestLockedFamily.unlock_cost_credits),
                    cost: cheapestLockedFamily.unlock_cost_credits,
                  })}
                </p>
                <div className="progress-bar">
                  <div
                    className="progress-bar-fill"
                    style={{
                      width: `${Math.min(100, (balance / cheapestLockedFamily.unlock_cost_credits) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            )}
          </>
        )}
      </section>

      <section className="card">
        <h2>
          {t("dashboard.achievementsHeading")}{" "}
          {t("dashboard.achievementsCount", { earned: earnedIds.length, total: ACHIEVEMENTS.length })}
        </h2>
        <div className="achievement-grid">
          {ACHIEVEMENTS.map((achievement) => {
            const earned = earnedIds.includes(achievement.id);
            return (
              <div
                key={achievement.id}
                className={`achievement-badge ${earned ? "achievement-badge-earned" : "achievement-badge-locked"} ${poppingIds.has(achievement.id) ? "achievement-badge-pop" : ""}`}
                title={t(`achievements.${achievement.id}.description`)}
              >
                <span className="achievement-badge-icon">{achievement.icon}</span>
                <span className="achievement-badge-title">{t(`achievements.${achievement.id}.title`)}</span>
              </div>
            );
          })}
        </div>
      </section>

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
                    {RENTAL_STATUS_ICONS[rental.status]} {t(`rentalStatusBadge.${rental.status}`)}
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
