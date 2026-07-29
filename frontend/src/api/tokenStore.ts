const REFRESH_TOKEN_KEY = "flydaro_refresh_token";

// Access token lives in memory only (never persisted); refresh token is kept
// in localStorage so a page reload doesn't force a re-login. See the plan's
// noted risk: this is the simpler choice for two separate origins (SPA +
// API), traded off against httpOnly-cookie's stronger XSS posture.
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function setTokens(access: string, refresh: string): void {
  setAccessToken(access);
  setRefreshToken(refresh);
}

export function clearTokens(): void {
  setAccessToken(null);
  setRefreshToken(null);
}
