import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Input } from "../components/ui/Input";
import { LogIn } from "lucide-react";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, senha);
      const perfil = JSON.parse(atob(localStorage.getItem("epass_access_token")!.split(".")[1])).perfil;
      navigate(`/${perfil}/dashboard`, { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.detail || "Erro ao fazer login");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[480px]">
      <div className="mb-10">
        <img src="/logo.png" alt="Logo" className="h-20 object-contain" />
      </div>

      <h1 className="text-3xl font-extrabold text-gray-900 mb-1">Bem-vindo</h1>
      <p className="text-base text-gray-500 mb-8">Faça login com sua conta</p>

      {error && (
        <div className="p-4 text-sm text-danger-600 bg-danger-50 rounded-xl mb-6">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <Input
          label="E-mail"
          type="email"
          placeholder="seunome@epass.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
        />

        <div>
          <Input
            label="Senha"
            type="password"
            placeholder="••••••••"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            required
          />
          <div className="text-right mt-2">
            <button type="button" className="text-sm text-primary-500 hover:text-primary-600 font-medium">
              Esqueceu sua senha?
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3.5 text-sm font-semibold text-white rounded-xl bg-gradient-to-r from-primary-500 to-orange-400 hover:from-primary-600 hover:to-orange-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary-500/25"
        >
          {loading ? (
            <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <LogIn className="h-5 w-5" />
          )}
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}
