import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "../auth/tokenStore";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export const apiClient = axios.create({ baseURL });

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

async function performRefresh(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  // Bare axios call (not apiClient) so this never re-triggers the interceptor.
  const { data } = await axios.post<{ access: string; refresh?: string }>(
    `${baseURL}/auth/token/refresh/`,
    { refresh }
  );
  setAccessToken(data.access);
  if (data.refresh) setRefreshToken(data.refresh); // ROTATE_REFRESH_TOKENS is on
  return data.access;
}

// Shared across ALL callers (the 401 retry below, and AuthContext's mount
// bootstrap) so concurrent refreshes — e.g. React StrictMode double-invoking
// an effect, or two tabs — collapse into one request instead of racing two
// rotations of the same one-time-use refresh token (the loser gets a 401
// and would otherwise wipe out a session the winner just restored).
let refreshPromise: Promise<string | null> | null = null;

export function refreshAccessToken(): Promise<string | null> {
  refreshPromise ??= performRefresh().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;

    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true;
      try {
        const newAccess = await refreshAccessToken();
        if (newAccess) {
          original.headers.Authorization = `Bearer ${newAccess}`;
          return apiClient(original);
        }
      } catch {
        // fall through to clearing tokens below
      }
      clearTokens();
      window.location.assign("/login");
    }
    return Promise.reject(error);
  }
);
