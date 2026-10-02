import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
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
  const reduceMotion = useReducedMotion();

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

  const container = {
    hidden: {},
    visible: {
      transition: { staggerChildren: 0.07, delayChildren: 0.12 },
    },
  };

  const item = {
    hidden: reduceMotion ? { opacity: 0 } : { opacity: 0, y: 18 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { type: "spring" as const, stiffness: 300, damping: 26 },
    },
  };

  return (
    <motion.div
      className="flex flex-col min-h-[480px]"
      variants={container}
      initial="hidden"
      animate="visible"
    >
      <motion.div className="mb-10" variants={item}>
        <motion.img
          src="/logo.png"
          alt="Logo"
          className="h-20 object-contain"
          animate={reduceMotion ? undefined : { y: [0, -5, 0] }}
          transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
        />
      </motion.div>

      <motion.h1
        className="text-3xl font-extrabold text-gray-900 dark:text-gray-100 mb-1"
        variants={item}
      >
        <span className="epass-gradient-text">Bem-vindo</span>
      </motion.h1>
      <motion.p className="text-base text-gray-500 dark:text-gray-400 mb-8" variants={item}>
        Faça login com sua conta
      </motion.p>

      <AnimatePresence mode="wait">
        {error && (
          <motion.div
            key={error}
            className="p-4 text-sm text-danger-600 bg-danger-50 dark:bg-danger-900/20 rounded-xl mb-6 border border-danger-500/20"
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -10, x: -8 }}
            animate={
              reduceMotion
                ? { opacity: 1 }
                : { opacity: 1, y: 0, x: [0, -8, 8, -5, 5, 0] }
            }
            exit={{ opacity: 0, y: -8 }}
            transition={{
              opacity: { duration: 0.2 },
              y: { duration: 0.2 },
              x: { duration: 0.4 },
            }}
            role="alert"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.form onSubmit={handleSubmit} className="space-y-6">
        <motion.div variants={item}>
          <Input
            label="E-mail"
            type="email"
            placeholder="seunome@epass.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </motion.div>

        <motion.div variants={item}>
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
              <button
                type="button"
                className="text-sm text-primary-500 hover:text-primary-600 font-medium transition-colors"
              >
                Esqueceu sua senha?
              </button>
            </div>
          </div>
        </motion.div>

        <motion.div variants={item}>
          <motion.button
            type="submit"
            disabled={loading}
            className="w-full relative flex items-center justify-center gap-2 overflow-hidden px-4 py-3.5 text-sm font-semibold text-white rounded-xl bg-gradient-to-r from-primary-500 to-orange-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-epass-primary-lg"
            whileHover={
              reduceMotion || loading
                ? undefined
                : { scale: 1.02, y: -2 }
            }
            whileTap={reduceMotion ? undefined : { scale: 0.98 }}
            transition={{ type: "spring", stiffness: 420, damping: 24 }}
          >
            {!reduceMotion && (
              <motion.span
                className="absolute inset-y-0 -left-full w-1/2 bg-gradient-to-r from-transparent via-white/35 to-transparent skew-x-[-20deg]"
                animate={{ x: ["0%", "320%"] }}
                transition={{ duration: 2.6, repeat: Infinity, repeatDelay: 2.4, ease: "easeInOut" }}
                aria-hidden="true"
              />
            )}

            <AnimatePresence mode="wait" initial={false}>
              {loading ? (
                <motion.span
                  key="loading"
                  className="flex items-center gap-2"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.18 }}
                >
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Entrando...
                </motion.span>
              ) : (
                <motion.span
                  key="idle"
                  className="flex items-center gap-2"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.18 }}
                >
                  <LogIn className="h-5 w-5" />
                  Entrar
                </motion.span>
              )}
            </AnimatePresence>
          </motion.button>
        </motion.div>
      </motion.form>
    </motion.div>
  );
}
