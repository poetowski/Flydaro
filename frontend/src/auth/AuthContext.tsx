import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import { getAccessToken, getRefreshToken, onForcedLogout } from "../api/tokenStore";

interface AuthContextValue {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // On a fresh page load there's no access token yet, only a persisted
    // refresh token. Treat that as authenticated -- the API client silently
    // refreshes on the first request's 401.
    setIsAuthenticated(Boolean(getAccessToken() || getRefreshToken()));
    setIsLoading(false);
  }, []);

  useEffect(() => {
    // A refresh-token rejection deep inside api/client.ts calls this outside
    // of any component -- without this subscription, isAuthenticated would
    // stay stale and RequireAuth would never redirect to /login.
    return onForcedLogout(() => setIsAuthenticated(false));
  }, []);

  async function login(email: string, password: string) {
    await authApi.login(email, password);
    setIsAuthenticated(true);
  }

  async function signup(email: string, password: string, displayName: string) {
    await authApi.signup(email, password, displayName);
    setIsAuthenticated(true);
  }

  async function logout() {
    await authApi.logout();
    setIsAuthenticated(false);
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
