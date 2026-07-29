import { apiRequest } from "./client";
import { clearTokens, getRefreshToken, setTokens } from "./tokenStore";

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function signup(email: string, password: string, displayName: string): Promise<void> {
  const tokens = await apiRequest<TokenPair>("/auth/signup", {
    method: "POST",
    body: { email, password, display_name: displayName },
    auth: false,
  });
  setTokens(tokens.access_token, tokens.refresh_token);
}

export async function login(email: string, password: string): Promise<void> {
  const tokens = await apiRequest<TokenPair>("/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
  setTokens(tokens.access_token, tokens.refresh_token);
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await apiRequest("/auth/logout", {
        method: "POST",
        body: { refresh_token: refreshToken },
        auth: false,
      });
    } catch {
      // best-effort revoke; clear local tokens regardless
    }
  }
  clearTokens();
}
