// Access token: kept in memory only (never persisted) — cleared on full page reload.
// Refresh token: persisted in localStorage so a reload doesn't force re-login.
// See docs note in AuthContext.tsx about the httpOnly-cookie upgrade path.

const REFRESH_KEY = "smm_refresh_token";

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    localStorage.setItem(REFRESH_KEY, token);
  } else {
    localStorage.removeItem(REFRESH_KEY);
  }
}

export function clearTokens(): void {
  setAccessToken(null);
  setRefreshToken(null);
}
