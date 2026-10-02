import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { subscribeNotificacoes, type NotificacaoRealtime } from "../api/realtime";
import { useAuth } from "./AuthContext";
import { springPop } from "../components/motion/transitions";

interface NotificacaoToast extends NotificacaoRealtime {
  toastId: string;
  hora: string;
}

interface RealtimeContextType {
  conectado: boolean;
  toasts: NotificacaoToast[];
  dispensar: (id: string) => void;
}

const RealtimeContext = createContext<RealtimeContextType | null>(null);

const MAX_TOASTS = 3;
const DURACAO_TOAST_MS = 9000;

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [conectado, setConectado] = useState(false);
  const [toasts, setToasts] = useState<NotificacaoToast[]>([]);
  const timersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const dispensar = useCallback((toastId: string) => {
    setToasts((prev) => prev.filter((t) => t.toastId !== toastId));
    const timer = timersRef.current[toastId];
    if (timer) {
      clearTimeout(timer);
      delete timersRef.current[toastId];
    }
  }, []);

  const aoReceber = useCallback(
    (evento: { evento: string; notificacao: NotificacaoRealtime }) => {
      if (evento.evento !== "notificacao" || !evento.notificacao) return;
      const notificacao = evento.notificacao;

      // Atualiza contador e listas sem refresh manual.
      queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes-nao-lidas"] });
      if (notificacao.entidade_tipo === "aviso") {
        queryClient.invalidateQueries({ queryKey: ["avisos"] });
        if (notificacao.entidade_id) {
          queryClient.invalidateQueries({ queryKey: ["aviso", notificacao.entidade_id] });
        }
      }

      const toastId = `${notificacao.id}-${Date.now()}`;
      const novo: NotificacaoToast = {
        ...notificacao,
        toastId,
        hora: "Agora",
      };
      setToasts((prev) => [...prev.slice(-(MAX_TOASTS - 1)), novo]);
      timersRef.current[toastId] = setTimeout(() => dispensar(toastId), DURACAO_TOAST_MS);
    },
    [dispensar, queryClient],
  );

  useEffect(() => {
    if (!isAuthenticated) {
      setConectado(false);
      setToasts([]);
      return;
    }
    const cancelar = subscribeNotificacoes(aoReceber, setConectado);
    return () => cancelar();
  }, [isAuthenticated, aoReceber]);

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      Object.values(timers).forEach(clearTimeout);
    };
  }, []);

  const abrir = useCallback(
    (toast: NotificacaoToast) => {
      dispensar(toast.toastId);
      const perfil = user?.perfil ?? "admin";
      const dados = (toast.dados ?? {}) as Record<string, unknown>;
      const ocorrenciaId =
        (dados.ocorrencia_id as string | undefined) ??
        (toast.entidade_tipo === "ocorrencia" ? toast.entidade_id ?? undefined : undefined);
      const avisoId =
        (dados.aviso_id as string | undefined) ??
        (toast.entidade_tipo === "aviso" ? toast.entidade_id ?? undefined : undefined);
      if (ocorrenciaId) {
        navigate(`/${perfil}/ocorrencias?ocorrencia=${ocorrenciaId}`);
      } else if (avisoId) {
        navigate(`/${perfil}/avisos?aviso=${avisoId}`);
      } else {
        navigate(`/${perfil}/notificacoes`);
      }
    },
    [dispensar, navigate, user?.perfil],
  );

  return (
    <RealtimeContext.Provider value={{ conectado, toasts, dispensar }}>
      {children}
      {/* Toasts laterais de tempo real */}
      <div className="fixed bottom-4 right-4 z-[90] w-[calc(100%-2rem)] max-w-sm space-y-2">
        <AnimatePresence mode="popLayout" initial={false}>
          {toasts.map((t) => (
            <motion.button
              layout
              key={t.toastId}
              onClick={() => abrir(t)}
              initial={{ opacity: 0, x: 48, scale: 0.92 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 48, scale: 0.92, transition: { duration: 0.2 } }}
              transition={springPop}
              className="group w-full text-left bg-card dark:bg-card-dark border border-gray-200 dark:border-gray-700 border-l-4 border-l-primary-500 rounded-xl shadow-epass-md p-4 hover:shadow-epass-lg transition-shadow"
            >
              <div className="flex items-start gap-3">
                <motion.span
                  className="text-lg leading-none"
                  aria-hidden
                  animate={{ scale: [1, 1.18, 1], rotate: [0, 8, 0] }}
                  transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
                >
                  🔔
                </motion.span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {t.titulo}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-300 mt-0.5 line-clamp-2">
                    {t.mensagem}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">{t.hora}</p>
                </div>
                <span
                  role="button"
                  tabIndex={-1}
                  onClick={(e) => {
                    e.stopPropagation();
                    dispensar(t.toastId);
                  }}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-xs opacity-0 transition-opacity group-hover:opacity-100"
                >
                  fechar
                </span>
              </div>
            </motion.button>
          ))}
        </AnimatePresence>
      </div>
    </RealtimeContext.Provider>
  );
}

export function useRealtime() {
  const context = useContext(RealtimeContext);
  if (!context) throw new Error("useRealtime must be used within RealtimeProvider");
  return context;
}
