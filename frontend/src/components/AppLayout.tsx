import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { listMyRentals } from "../api/rentals";
import { getWallet } from "../api/wallet";
import { useAuth } from "../auth/AuthContext";

export function AppLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
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
            Dashboard
          </NavLink>
          <NavLink to="/wallet-ledger">Wallet Ledger</NavLink>
          <NavLink to="/flights">Flight Board</NavLink>
          <NavLink to="/rentals">Rental History</NavLink>
          <NavLink to="/licenses">Licenses</NavLink>
          <NavLink to="/the-crew">Crew</NavLink>
          <NavLink to="/board-of-fame" className="nav-right-group">
            Board of Fame
          </NavLink>
          <NavLink to="/our-story">Our Story</NavLink>
        </nav>
        <div className="header-right">
          {rewardsReadyCount > 0 && (
            <NavLink to="/rentals" className="badge-reward-ready">
              {rewardsReadyCount} ready to claim
            </NavLink>
          )}
          <span className="wallet-badge">{wallet ? `${wallet.balance_credits} cr` : "..."}</span>
          <button onClick={handleLogout}>Log out</button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
