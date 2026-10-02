import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Menu, Bell, Wifi, WifiOff, CheckCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../../contexts/AuthContext";
import { useRealtime } from "../../contexts/RealtimeContext";
import { notificacoesApi, type Notificacao, type TipoNotificacao } from "../../api/endpoints";
import { dropdownVariants, springSoft } from "../motion/transitions";
import { BranchedMenu, type BranchedMenuItem } from "../ui/BranchedMenu";

interface HeaderProps {
  onMenuClick: () => void;
}

const TIPO_ICONE: Record<TipoNotificacao, string> = {
  sistema: "⚙️",
  cantina: "🍽️",
  boletim: "📘",
  ocorrencia: "⚠️",
  aviso: "📣",
  agenda: "📅",
  financeiro: "💳",
  nota: "📝",
  frequencia: "✅",
};

function tempoRelativo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutos = Math.floor(diff / 60000);
  if (minutos < 1) return "Agora";
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `${horas} h`;
  const dias = Math.floor(horas / 24);
  return dias === 1 ? "Ontem" : `${dias} dias`;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { conectado } = useRealtime();
  const [painelAberto, setPainelAberto] = useState(false);
  const [ultimaAberta, setUltimaAberta] = useState<string | undefined>();
  const painelRef = useRef<HTMLDivElement | null>(null);
  const reduceMotion = useReducedMotion();

  const { data: naoLidas } = useQuery({
    queryKey: ["notificacoes-nao-lidas"],
    queryFn: notificacoesApi.naoLidas,
    refetchInterval: conectado ? 120000 : 60000,
    enabled: !!user,
  });

  const { data: recentes } = useQuery({
    queryKey: ["notificacoes", false, 1, "header"],
    queryFn: () => notificacoesApi.list({ page: 1, size: 6 }),
    enabled: !!user && painelAberto,
  });

  const marcarTodas = useMutation({
    mutationFn: notificacoesApi.marcarTodasLidas,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes-nao-lidas"] });
    },
  });

  const marcarLida = useMutation({
    mutationFn: (id: string) => notificacoesApi.marcarLida(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes-nao-lidas"] });
    },
  });

  useEffect(() => {
    if (!painelAberto) return;
    const handler = (e: MouseEvent) => {
      if (painelRef.current && !painelRef.current.contains(e.target as Node)) {
        setPainelAberto(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [painelAberto]);

  const total = naoLidas?.total ?? 0;

  const notificacoes = recentes?.items ?? [];

  // Mesma lista, agora como itens do Branched Menu: o conteúdo rico continua
  // idêntico, mas as ramificações e a linha de acento ligam cada notificação
  // ao tronco do painel.
  const notificationItems = useMemo<BranchedMenuItem[]>(
    () =>
      notificacoes.map((n) => ({
        value: n.id,
        label: n.titulo,
        trailing: !n.lida ? (
          <span className="h-2 w-2 rounded-full bg-primary-500 flex-shrink-0 animate-pulse" />
        ) : null,
      })),
    [notificacoes],
  );

  const abrirNotificacao = (n: Notificacao) => {
    if (!n.lida) marcarLida.mutate(n.id);
    setUltimaAberta(n.id);
    setPainelAberto(false);
    const dados = (n.dados ?? {}) as Record<string, unknown>;
    const ocorrenciaId =
      (dados.ocorrencia_id as string | undefined) ??
      (n.entidade_tipo === "ocorrencia" ? n.entidade_id ?? undefined : undefined);
    const avisoId =
      (dados.aviso_id as string | undefined) ??
      (n.entidade_tipo === "aviso" ? n.entidade_id ?? undefined : undefined);
    if (ocorrenciaId) {
      navigate(`/${user?.perfil}/ocorrencias?ocorrencia=${ocorrenciaId}`);
    } else if (avisoId) {
      navigate(`/${user?.perfil}/avisos?aviso=${avisoId}`);
    } else {
      navigate(`/${user?.perfil}/notificacoes`);
    }
  };

  return (
    <header className="h-16 bg-card dark:bg-card-dark border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-4 md:px-6 gap-4">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onMenuClick}
          className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 md:hidden flex-shrink-0"
          aria-label="Abrir menu"
        >
          <Menu className="h-5 w-5" />
        </button>
            <motion.span
              className="hidden md:flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500"
              title={conectado ? "Tempo real conectado" : "Reconectando em tempo real"}
            >
              <motion.span
                className="relative flex h-3.5 w-3.5 items-center justify-center"
                animate={reduceMotion ? undefined : { scale: conectado ? [1, 1.15, 1] : 1 }}
                transition={conectado ? { duration: 2.4, repeat: Infinity, ease: "easeInOut" } : undefined}
              >
                {conectado ? (
                  <>
                    <span className="absolute inset-0 rounded-full bg-success-500/40 animate-ring" />
                    <Wifi className="h-3.5 w-3.5 text-success-500 relative" />
                  </>
                ) : (
                  <WifiOff className="h-3.5 w-3.5 text-gray-300" />
                )}
              </motion.span>
              {conectado ? "Tempo real" : "Polling"}
            </motion.span>
      </div>

      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="relative" ref={painelRef}>
          <button
            onClick={() => setPainelAberto((v) => !v)}
            className="relative p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label={`Notificações${total > 0 ? ` (${total} não lidas)` : ""}`}
            aria-expanded={painelAberto}
          >
            <motion.span
              animate={
                reduceMotion || total === 0
                  ? { rotate: 0 }
                  : { rotate: [0, -14, 12, -8, 0] }
              }
              transition={{ duration: 0.6, ease: "easeInOut" }}
              key={total}
            >
              <Bell className="h-5 w-5" />
            </motion.span>
            <AnimatePresence>
              {total > 0 && (
                <motion.span
                  key={total}
                  initial={{ scale: 0.3, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.3, opacity: 0 }}
                  transition={springSoft}
                  className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-danger-500 text-white text-[10px] font-bold flex items-center justify-center shadow-epass"
                >
                  {total > 99 ? "99+" : total}
                </motion.span>
              )}
            </AnimatePresence>
          </button>

          <AnimatePresence>
            {painelAberto && (
              <motion.div
                key="painel"
                variants={dropdownVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                className="absolute right-0 mt-2 w-80 sm:w-96 bg-card dark:bg-card-dark border border-gray-200 dark:border-gray-700 rounded-xl shadow-epass-xl overflow-hidden z-50 origin-top-right"
              >
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                <div>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    Central de Notificações
                  </p>
                  <p className="text-xs text-gray-400">
                    {total > 0 ? `${total} não lida(s)` : "Tudo em dia"}
                  </p>
                </div>
                <button
                  onClick={() => marcarTodas.mutate()}
                  disabled={total === 0 || marcarTodas.isPending}
                  className="flex items-center gap-1 text-xs text-primary-500 hover:text-primary-600 disabled:opacity-40"
                >
                  <CheckCheck className="h-3.5 w-3.5" />
                  Marcar todas
                </button>
              </div>

              <div className="max-h-80 overflow-y-auto py-1.5 epass-scrollbar">
                {notificacoes.length === 0 ? (
                  <p className="px-4 py-8 text-center text-sm text-gray-400">
                    Nenhuma notificação.
                  </p>
                ) : (
                  <div className="px-3">
                    <BranchedMenu
                      items={notificationItems}
                      label="Notificações recentes"
                      activeValue={ultimaAberta}
                      onSelect={(value) => {
                        const alvo = notificacoes.find((n) => n.id === value);
                        if (alvo) abrirNotificacao(alvo);
                      }}
                      width={320}
                      rowHeight={56}
                      indent={30}
                      branchLeaves
                      renderItem={(item) => {
                        const n = notificacoes.find((x) => x.id === item.value);
                        if (!n) return null;
                        return (
                          <>
                            <span aria-hidden="true" className="text-base leading-none shrink-0">
                              {TIPO_ICONE[n.tipo] ?? "🔔"}
                            </span>
                            <span className="bm__stack">
                              <span className="bm__title">{n.titulo}</span>
                              <span className="bm__desc">{n.mensagem}</span>
                              <span className="bm__meta">{tempoRelativo(n.created_at)}</span>
                            </span>
                            {item.trailing ? (
                              <span className="bm__trailing">{item.trailing}</span>
                            ) : null}
                          </>
                        );
                      }}
                    />
                  </div>
                )}
              </div>

              <button
                onClick={() => {
                  setPainelAberto(false);
                  navigate(`/${user?.perfil}/notificacoes`);
                }}
                className="w-full px-4 py-2.5 text-center text-sm font-medium text-primary-500 hover:bg-gray-50 dark:hover:bg-gray-800/40 border-t border-gray-200 dark:border-gray-700 transition-colors"
              >
                Ver todas
              </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="text-right hidden sm:block">
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate max-w-[120px] md:max-w-none">
            {user?.nome}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{user?.perfil}</p>
        </div>
        <div className="h-9 w-9 rounded-full bg-primary-500 flex items-center justify-center text-white font-medium text-sm flex-shrink-0">
          {user?.nome?.charAt(0)?.toUpperCase() || "U"}
        </div>
      </div>
    </header>
  );
}
