import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { api, setTokens, clearTokens, hasStoredTokens } from "../api/client";
import type { User } from "../types/api";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(hasStoredTokens());

  useEffect(() => {
    if (hasStoredTokens()) {
      api
        .get<User>("/auth/me")
        .then(({ data }) => setUser(data))
        .catch(() => clearTokens())
        .finally(() => setIsLoading(false));
    }
  }, []);

  const login = useCallback(async (email: string, senha: string) => {
    const { data: tokens } = await api.post("/auth/login", { email, password: senha });
    setTokens(tokens.access_token, tokens.refresh_token);
    const { data: userData } = await api.get<User>("/auth/me");
    setUser(userData);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout", { refresh_token: localStorage.getItem("epass_refresh_token") });
    } catch {
    } finally {
      clearTokens();
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
