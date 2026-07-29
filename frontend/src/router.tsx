import { createBrowserRouter } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { AppLayout } from "./components/AppLayout";
import { BetHistoryPage } from "./routes/BetHistoryPage";
import { BetPlacementPage } from "./routes/BetPlacementPage";
import { DashboardPage } from "./routes/DashboardPage";
import { FlightBoardPage } from "./routes/FlightBoardPage";
import { LoginPage } from "./routes/LoginPage";
import { SignupPage } from "./routes/SignupPage";

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
          { path: "/flights/:flightId/bet", element: <BetPlacementPage /> },
          { path: "/bets", element: <BetHistoryPage /> },
        ],
      },
    ],
  },
]);
