import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import axios from "axios";
import { api, setTokens, clearTokens, getStoredAccessToken, setOnForcedLogout } from "../api/client";
import * as SecureStore from "../services/storage";
import { desregistrarPushToken } from "../services/pushNotifications";
import type { User } from "../types";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<User | null>;
  applyUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();

    (async () => {
      try {
        const token = await getStoredAccessToken();
        if (!token) {
          if (mounted) setIsLoading(false);
          return;
        }
        const { data } = await api.get("/auth/me", { signal: controller.signal });
        if (mounted) setUser(data);
      } catch (err) {
        if (mounted && !axios.isCancel(err)) {
          await clearTokens();
        }
      } finally {
        if (mounted) setIsLoading(false);
      }
    })();

    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    setOnForcedLogout(async () => {
      await clearTokens();
      setUser(null);
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post("/auth/login", { email, password });
    await setTokens(data.access_token, data.refresh_token);
    const { data: userData } = await api.get("/auth/me");
    setUser(userData);
  }, []);

  const applyUser = useCallback((nextUser: User) => {
    setUser(nextUser);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const { data } = await api.get<User>("/auth/me");
      setUser(data);
      return data;
    } catch (err) {
      if (axios.isCancel(err)) return null;
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      const refreshToken = await SecureStore.getItemAsync("epass_refresh_token");
      if (refreshToken) {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      }
    } catch {
    } finally {
      // Remove o token de push do backend antes de limpar a sessão.
      await desregistrarPushToken();
      await clearTokens();
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        refreshUser,
        applyUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
