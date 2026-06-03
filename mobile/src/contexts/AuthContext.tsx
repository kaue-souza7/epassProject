import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { api, setTokens, clearTokens } from "../api/client";

interface User {
  id: string;
  nome: string;
  email: string;
  perfil: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const login = useCallback(async (email: string, senha: string) => {
    const { data } = await api.post("/auth/login", { email, senha });
    await setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  }, []);

  const logout = useCallback(async () => {
    await clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
