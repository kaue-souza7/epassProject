import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificacoesApi, type Notificacao, type TipoNotificacao } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { PageHeader } from "../../components/layout/PageHeader";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/ErrorState";
import { Skeleton } from "../../components/ui/Skeleton";
import { CheckCheck } from "lucide-react";

const TIPO_LABEL: Record<TipoNotificacao, string> = {
  sistema: "Sistema",
  cantina: "Cantina",
  boletim: "Boletim",
  ocorrencia: "Ocorrência",
  aviso: "Aviso",
  agenda: "Agenda",
  financeiro: "Financeiro",
  nota: "Nota",
  frequencia: "Frequência",
};

const TIPO_VARIANT: Record<TipoNotificacao, "default" | "info" | "warning" | "success" | "danger"> = {
  sistema: "default",
  cantina: "warning",
  boletim: "info",
  ocorrencia: "danger",
  aviso: "info",
  agenda: "default",
  financeiro: "success",
  nota: "info",
  frequencia: "info",
};

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

function grupoDoDia(iso: string): string {
  const data = new Date(iso);
  const hoje = new Date();
  const ontem = new Date();
  ontem.setDate(hoje.getDate() - 1);
  const mesmoDia = (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate();
  if (mesmoDia(data, hoje)) return "Hoje";
  if (mesmoDia(data, ontem)) return "Ontem";
  return data.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: data.getFullYear() !== hoje.getFullYear() ? "numeric" : undefined,
  });
}

export function NotificacoesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [apenasNaoLidas, setApenasNaoLidas] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["notificacoes", apenasNaoLidas, page],
    queryFn: () =>
      notificacoesApi.list({
        apenas_nao_lidas: apenasNaoLidas || undefined,
        page,
        size: 20,
      }),
  });

  const { data: naoLidas } = useQuery({
    queryKey: ["notificacoes-nao-lidas"],
    queryFn: notificacoesApi.naoLidas,
    refetchInterval: 60000,
  });

  const marcarMutation = useMutation({
    mutationFn: (id: string) => notificacoesApi.marcarLida(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes-nao-lidas"] });
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao marcar notificação como lida");
    },
  });

  const marcarTodasMutation = useMutation({
    mutationFn: notificacoesApi.marcarTodasLidas,
    onSuccess: (res) => {
      toast("success", `${res.marcadas} notificação(ões) marcada(s) como lida(s)`);
      queryClient.invalidateQueries({ queryKey: ["notificacoes"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes-nao-lidas"] });
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao marcar notificações");
    },
  });

  const notificacoes = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const grupos = useMemo(() => {
    const mapa = new Map<string, Notificacao[]>();
    for (const n of notificacoes) {
      const grupo = grupoDoDia(n.created_at);
      const lista = mapa.get(grupo) ?? [];
      lista.push(n);
      mapa.set(grupo, lista);
    }
    return [...mapa.entries()];
  }, [notificacoes]);

  const abrir = (n: Notificacao) => {
    if (!n.lida) marcarMutation.mutate(n.id);
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
    }
  };

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Notificações" }]} />
        <Card>
          <ErrorState
            title="Erro ao carregar notificações"
            message="Não foi possível carregar as notificações."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["notificacoes"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Notificações" }]} />
      <PageHeader
        title="Central de Notificações"
        description={
          naoLidas
            ? `${naoLidas.total} não lida(s) de ${total} notificação(ões)`
            : `${total} notificação(ões)`
        }
        showNew={false}
      >
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={apenasNaoLidas}
            onChange={(e) => {
              setApenasNaoLidas(e.target.checked);
              setPage(1);
            }}
          />
          Apenas não lidas
        </label>
        <Button
          variant="outline"
          size="sm"
          onClick={() => marcarTodasMutation.mutate()}
          loading={marcarTodasMutation.isPending}
          disabled={(naoLidas?.total ?? 0) === 0}
        >
          <CheckCheck className="h-4 w-4 mr-2" />
          Marcar todas como lidas
        </Button>
      </PageHeader>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      ) : notificacoes.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <p className="text-lg text-gray-500 dark:text-gray-400">Tudo em dia</p>
            <p className="text-sm text-gray-400 mt-1">Nenhuma notificação por aqui.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-6">
          {grupos.map(([grupo, itens]) => (
            <div key={grupo}>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
                {grupo}
              </p>
              <div className="space-y-2">
                {itens.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => abrir(n)}
                    className={`w-full text-left rounded-xl border p-4 transition-shadow hover:shadow-md bg-card dark:bg-card-dark border-gray-200 dark:border-gray-700 ${
                      n.lida ? "" : "border-l-4 border-l-primary-500"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span aria-hidden className="text-lg leading-none mt-0.5">
                        {TIPO_ICONE[n.tipo] ?? "🔔"}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge variant={TIPO_VARIANT[n.tipo]}>{TIPO_LABEL[n.tipo]}</Badge>
                          <h3 className="font-medium text-gray-900 dark:text-gray-100">
                            {n.titulo}
                          </h3>
                          {!n.lida && <Badge variant="danger">Nova</Badge>}
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                          {n.mensagem}
                        </p>
                        <p className="text-xs text-gray-400 mt-2">
                          {new Date(n.created_at).toLocaleString("pt-BR")}
                        </p>
                      </div>
                      {!n.lida && (
                        <span
                          role="button"
                          tabIndex={-1}
                          onClick={(e) => {
                            e.stopPropagation();
                            marcarMutation.mutate(n.id);
                          }}
                          className="text-xs text-primary-500 hover:text-primary-600 flex-shrink-0"
                        >
                          Marcar lida
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-6">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Anterior
          </Button>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Página {page} de {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Próxima
          </Button>
        </div>
      )}
    </div>
  );
}
