import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { getCurrentUser } from "../api/auth";
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
  const { data: currentUser } = useQuery({ queryKey: ["currentUser"], queryFn: getCurrentUser });

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
          <NavLink to="/flights">Flight Board</NavLink>
          <NavLink to="/rentals">Rental History</NavLink>
          <NavLink to="/licenses">Licenses</NavLink>
          {currentUser?.is_admin && <NavLink to="/admin">Admin</NavLink>}
        </nav>
        <div className="header-right">
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
