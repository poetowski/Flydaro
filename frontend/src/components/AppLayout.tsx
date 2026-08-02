import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { listMyRentals } from "../api/rentals";
import { getWallet } from "../api/wallet";
import { useAuth } from "../auth/AuthContext";
import { useLanguage } from "../i18n";
import { PAGE_ICONS } from "../lib/pageIcons";
import { LanguageSwitcher } from "./LanguageSwitcher";

export function AppLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const { t, tPlural } = useLanguage();
  const { data: wallet } = useQuery({
    queryKey: ["wallet"],
    queryFn: getWallet,
    refetchInterval: 15000,
  });
  const { data: resolvedRentals } = useQuery({
    queryKey: ["rentals", "mine", "RESOLVED"],
    queryFn: () => listMyRentals("RESOLVED"),
    refetchInterval: 15000,
  });
  const rewardsReadyCount = resolvedRentals?.length ?? 0;

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="brand">Flydaro</span>
        <nav>
          <NavLink to="/" end>
            {PAGE_ICONS["/"]} {t("nav.dashboard")}
          </NavLink>
          <NavLink to="/wallet-ledger">
            {PAGE_ICONS["/wallet-ledger"]} {t("nav.walletLedger")}
          </NavLink>
          <NavLink to="/flights">
            {PAGE_ICONS["/flights"]} {t("nav.flightBoard")}
          </NavLink>
          <NavLink to="/rentals">
            {PAGE_ICONS["/rentals"]} {t("nav.rentalHistory")}
          </NavLink>
          <NavLink to="/licenses">
            {PAGE_ICONS["/licenses"]} {t("nav.licenses")}
          </NavLink>
          <NavLink to="/the-crew">
            {PAGE_ICONS["/the-crew"]} {t("nav.crew")}
          </NavLink>
          <NavLink to="/board-of-fame" className="nav-right-group">
            {PAGE_ICONS["/board-of-fame"]} {t("nav.boardOfFame")}
          </NavLink>
          <NavLink to="/our-story">
            {PAGE_ICONS["/our-story"]} {t("nav.ourStory")}
          </NavLink>
        </nav>
        <div className="header-right">
          {rewardsReadyCount > 0 && (
            <NavLink to="/rentals" className="badge-reward-ready">
              {tPlural("appLayout.readyToClaim", rewardsReadyCount)}
            </NavLink>
          )}
          <span className="wallet-badge">
            {wallet ? `${wallet.balance_credits} ${t("common.creditsShort")}` : "..."}
          </span>
          <LanguageSwitcher />
          <button onClick={handleLogout}>{t("nav.logOut")}</button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
