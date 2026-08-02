import type { Airport } from "../api/airports";
import type { AircraftFamily } from "../api/aircraftFamilies";
import type { CrewOverviewEntry } from "../api/crew";
import type { MyRank } from "../api/leaderboard";
import type { Rental } from "../api/rentals";
import type { Wallet, WalletLedgerEntry } from "../api/wallet";

export interface AchievementData {
  rentals: Rental[];
  ledger: WalletLedgerEntry[];
  wallet: Wallet | undefined;
  airports: Airport[];
  aircraftFamilies: AircraftFamily[];
  crewOverview: CrewOverviewEntry[];
  myRank: MyRank | undefined;
}

export interface Achievement {
  id: string;
  icon: string;
  computeEarned: (data: AchievementData) => boolean;
}

function ledgerHasReason(ledger: WalletLedgerEntry[], reason: string): boolean {
  return ledger.some((entry) => entry.reason === reason);
}

function claimedCount(rentals: Rental[]): number {
  return rentals.filter((rental) => rental.status === "CLAIMED").length;
}

export const ACHIEVEMENTS: Achievement[] = [
  // Rentals placed
  { id: "FIRST_RENTAL", icon: "🛫", computeEarned: ({ rentals }) => rentals.length >= 1 },
  { id: "FIVE_RENTALS", icon: "📦", computeEarned: ({ rentals }) => rentals.length >= 5 },
  { id: "TWENTY_FIVE_RENTALS", icon: "🚀", computeEarned: ({ rentals }) => rentals.length >= 25 },
  { id: "FIFTY_RENTALS", icon: "🏆", computeEarned: ({ rentals }) => rentals.length >= 50 },

  // Landings / claims
  {
    id: "FIRST_LANDING",
    icon: "🛬",
    computeEarned: ({ rentals }) =>
      rentals.some((rental) => rental.status === "RESOLVED" || rental.status === "CLAIMED"),
  },
  {
    id: "FIRST_PAYDAY",
    icon: "💰",
    computeEarned: ({ rentals }) => rentals.some((rental) => rental.status === "CLAIMED"),
  },
  { id: "FREQUENT_FLYER", icon: "✈️", computeEarned: ({ rentals }) => claimedCount(rentals) >= 10 },
  { id: "VETERAN_FLYER", icon: "🎖️", computeEarned: ({ rentals }) => claimedCount(rentals) >= 25 },
  { id: "AVIATION_MOGUL", icon: "👑", computeEarned: ({ rentals }) => claimedCount(rentals) >= 50 },

  // Lifetime earnings
  {
    id: "RISING_STAR",
    icon: "⭐",
    computeEarned: ({ wallet }) => (wallet?.balance_credits ?? 0) >= 10_000,
  },
  {
    id: "HIGH_ROLLER",
    icon: "💎",
    computeEarned: ({ wallet }) => (wallet?.balance_credits ?? 0) >= 100_000,
  },
  {
    id: "TYCOON",
    icon: "🏦",
    computeEarned: ({ wallet }) => (wallet?.balance_credits ?? 0) >= 250_000,
  },
  {
    id: "BIG_WIN",
    icon: "🎉",
    computeEarned: ({ rentals }) => rentals.some((rental) => (rental.settlement_credits ?? 0) >= 2_000),
  },

  // Licensing / fleet
  {
    id: "LICENSED_PILOT",
    icon: "🪪",
    computeEarned: ({ ledger }) => ledgerHasReason(ledger, "license_purchase"),
  },
  {
    id: "GLOBE_TROTTER",
    icon: "🌍",
    computeEarned: ({ airports }) => airports.length > 0 && airports.every((a) => a.unlocked),
  },
  {
    id: "FLEET_MASTER",
    icon: "🛩️",
    computeEarned: ({ aircraftFamilies }) =>
      aircraftFamilies.length > 0 && aircraftFamilies.every((f) => f.unlocked),
  },
  {
    id: "EXPLORER",
    icon: "🗺️",
    // Scoped to paid (non-starter) airports only -- the 5 free starters are
    // already "unlocked" for every new account, so counting them here would
    // make this trivially earned at signup instead of a real milestone.
    computeEarned: ({ airports }) => {
      const paid = airports.filter((a) => a.unlock_cost_credits > 0);
      return paid.length > 0 && paid.filter((a) => a.unlocked).length >= Math.ceil(paid.length / 2);
    },
  },

  // Crew
  { id: "CREW_CHIEF", icon: "👷", computeEarned: ({ ledger }) => ledgerHasReason(ledger, "crew_hire") },
  {
    id: "FULL_ROSTER",
    icon: "👥",
    computeEarned: ({ crewOverview }) =>
      crewOverview.reduce((sum, entry) => sum + entry.crew_count, 0) >= 5,
  },
  {
    id: "MULTI_BASE",
    icon: "🏢",
    computeEarned: ({ crewOverview }) =>
      crewOverview.filter((entry) => entry.crew_count > 0).length >= 3,
  },

  // Route/fleet variety
  {
    id: "FREQUENT_ROUTES",
    icon: "🧭",
    computeEarned: ({ rentals }) =>
      new Set(rentals.map((r) => r.origin_airport_code).filter(Boolean)).size >= 3,
  },
  {
    id: "FLEET_VARIETY",
    icon: "🔀",
    computeEarned: ({ rentals }) =>
      new Set(rentals.map((r) => r.aircraft_family_code).filter(Boolean)).size >= 3,
  },

  // Leaderboard
  { id: "TOP_TEN", icon: "🏅", computeEarned: ({ myRank }) => (myRank?.rank ?? Infinity) <= 10 },

  // Well-rounded engagement
  {
    id: "WELL_ROUNDED",
    icon: "🎯",
    computeEarned: ({ ledger }) =>
      ["rental_fee", "settlement", "license_purchase", "crew_hire"].every((reason) =>
        ledgerHasReason(ledger, reason),
      ),
  },
];
