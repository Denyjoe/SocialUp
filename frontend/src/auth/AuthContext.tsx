import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  fetchMe,
  googleAuth,
  login as loginRequest,
  logout as logoutRequest,
} from "../api/endpoints/auth";
import { refreshAccessToken } from "../api/client";
import type { LoginPayload } from "../api/endpoints/auth";
import type { UserProfile } from "../types/api";
import {
  clearTokens,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from "./tokenStore";

interface AuthContextValue {
  user: UserProfile | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<UserProfile>;
  loginWithGoogle: (idToken: string, referralCode?: string) => Promise<UserProfile>;
  logout: () => Promise<void>;
  setUser: (user: UserProfile | null) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();

  // On first load, the access token is gone (it only ever lived in memory),
  // but a refresh token may still be in localStorage from a previous
  // session — use it to transparently restore the session.
  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!getRefreshToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const access = await refreshAccessToken();
        if (!access) throw new Error("no access token returned");
        const profile = await fetchMe();
        if (!cancelled) setUser(profile);
      } catch {
        clearTokens();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function login(payload: LoginPayload): Promise<UserProfile> {
    const data = await loginRequest(payload);
    setAccessToken(data.access);
    setRefreshToken(data.refresh);
    setUser(data.user);
    return data.user;
  }

  async function loginWithGoogle(idToken: string, referralCode?: string): Promise<UserProfile> {
    const data = await googleAuth(idToken, referralCode);
    setAccessToken(data.access);
    setRefreshToken(data.refresh);
    setUser(data.user);
    return data.user;
  }

  async function logout(): Promise<void> {
    const refresh = getRefreshToken();
    try {
      if (refresh) await logoutRequest(refresh);
    } finally {
      clearTokens();
      setUser(null);
      queryClient.clear();
    }
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, loginWithGoogle, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
