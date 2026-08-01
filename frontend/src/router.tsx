import { createBrowserRouter } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { AppLayout } from "./components/AppLayout";
import { BoardOfFamePage } from "./routes/BoardOfFamePage";
import { RentalHistoryPage } from "./routes/RentalHistoryPage";
import { RentalPlacementPage } from "./routes/RentalPlacementPage";
import { DashboardPage } from "./routes/DashboardPage";
import { FlightBoardPage } from "./routes/FlightBoardPage";
import { LicensesPage } from "./routes/LicensesPage";
import { LoginPage } from "./routes/LoginPage";
import { OurStoryPage } from "./routes/OurStoryPage";
import { SignupPage } from "./routes/SignupPage";
import { WalletLedgerPage } from "./routes/WalletLedgerPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/signup", element: <SignupPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <DashboardPage /> },
          { path: "/flights", element: <FlightBoardPage /> },
          { path: "/flights/:flightId/rent", element: <RentalPlacementPage /> },
          { path: "/rentals", element: <RentalHistoryPage /> },
          { path: "/licenses", element: <LicensesPage /> },
          { path: "/wallet-ledger", element: <WalletLedgerPage /> },
          { path: "/board-of-fame", element: <BoardOfFamePage /> },
          { path: "/our-story", element: <OurStoryPage /> },
        ],
      },
    ],
  },
]);
