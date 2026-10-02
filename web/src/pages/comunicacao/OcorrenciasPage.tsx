import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  classesApi,
  enrollmentsApi,
  ocorrenciasApi,
  type StatusOcorrencia,
  type TipoOcorrencia,
  type SeveridadeOcorrencia,
} from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { PageHeader } from "../../components/layout/PageHeader";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ErrorState } from "../../components/ui/ErrorState";
import { Skeleton } from "../../components/ui/Skeleton";

const MANAGE_ROLES = ["admin", "secretaria", "coordenador"];
const CREATE_ROLES = ["admin", "secretaria", "coordenador", "professor"];

const STATUS_LABEL: Record<StatusOcorrencia, string> = {
  aberta: "Aberta",
  em_andamento: "Em andamento",
  resolvida: "Resolvida",
  arquivada: "Arquivada",
};

const STATUS_VARIANT: Record<StatusOcorrencia, "info" | "warning" | "success" | "default"> = {
  aberta: "info",
  em_andamento: "warning",
  resolvida: "success",
  arquivada: "default",
};

const TIPO_LABEL: Record<TipoOcorrencia, string> = {
  comportamento: "Comportamento",
  saude: "Saúde",
  academico: "Acadêmico",
  outro: "Outro",
};

const SEVERIDADE_VARIANT: Record<SeveridadeOcorrencia, "info" | "warning" | "danger"> = {
  baixa: "info",
  media: "warning",
  alta: "danger",
};

const TRANSICOES: Record<StatusOcorrencia, StatusOcorrencia[]> = {
  aberta: ["em_andamento", "resolvida", "arquivada"],
  em_andamento: ["resolvida", "arquivada"],
  resolvida: ["arquivada"],
  arquivada: [],
};

export function OcorrenciasPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const canManage = !!user?.perfil && MANAGE_ROLES.includes(user.perfil);
  const canCreate = !!user?.perfil && CREATE_ROLES.includes(user.perfil);
  const isStaff = user?.perfil !== "responsavel" && user?.perfil !== "professor";

  const [searchParams, setSearchParams] = useSearchParams();
  const [statusFilter, setStatusFilter] = useState<StatusOcorrencia | "">("");
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);

  // Deep link de notificação: /.../ocorrencias?ocorrencia=<id>
  useEffect(() => {
    const ocorrenciaParam = searchParams.get("ocorrencia");
    if (ocorrenciaParam) {
      setDetailId(ocorrenciaParam);
      const next = new URLSearchParams(searchParams);
      next.delete("ocorrencia");
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);
  const [form, setForm] = useState({
    turma_id: "",
    aluno_id: "",
    responsavel_id: "",
    titulo: "",
    descricao: "",
    tipo: "comportamento" as TipoOcorrencia,
    severidade: "media" as SeveridadeOcorrencia,
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: ["ocorrencias", statusFilter, page],
    queryFn: () =>
      ocorrenciasApi.list({
        status: statusFilter || undefined,
        page,
        size: 20,
      }),
  });

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["ocorrencia", detailId],
    queryFn: () => ocorrenciasApi.getById(detailId as string),
    enabled: !!detailId,
  });

  const { data: turmas } = useQuery({
    queryKey: ["turmas-ocorrencia"],
    queryFn: () => classesApi.list({ only_active: true, size: 100 }),
    enabled: canCreate && showForm,
  });

  const { data: matriculas } = useQuery({
    queryKey: ["matriculas-ocorrencia", form.turma_id],
    queryFn: () => enrollmentsApi.list({ turma_id: form.turma_id, size: 100 }),
    enabled: canCreate && showForm && !!form.turma_id,
  });

  const criarMutation = useMutation({
    mutationFn: () =>
      ocorrenciasApi.create({
        turma_id: form.turma_id || null,
        aluno_id: form.aluno_id || null,
        responsavel_id: isStaff && form.responsavel_id ? form.responsavel_id : null,
        titulo: form.titulo,
        descricao: form.descricao,
        tipo: form.tipo,
        severidade: form.severidade,
      }),
    onSuccess: () => {
      toast("success", "Ocorrência registrada com sucesso");
      queryClient.invalidateQueries({ queryKey: ["ocorrencias"] });
      setShowForm(false);
      setForm({
        turma_id: "",
        aluno_id: "",
        responsavel_id: "",
        titulo: "",
        descricao: "",
        tipo: "comportamento",
        severidade: "media",
      });
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao registrar ocorrência");
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: StatusOcorrencia }) =>
      ocorrenciasApi.mudarStatus(id, status),
    onSuccess: () => {
      toast("success", "Status atualizado");
      queryClient.invalidateQueries({ queryKey: ["ocorrencias"] });
      queryClient.invalidateQueries({ queryKey: ["ocorrencia", detailId] });
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao atualizar status");
    },
  });

  const ocorrencias = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Ocorrências" }]} />
        <Card>
          <ErrorState
            title="Erro ao carregar ocorrências"
            message="Não foi possível carregar as ocorrências."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["ocorrencias"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Ocorrências" }]} />
      <PageHeader
        title="Ocorrências"
        description={`${total} ocorrência${total !== 1 ? "s" : ""} encontrada${total !== 1 ? "s" : ""}`}
        showNew={canCreate}
        onNew={() => setShowForm(true)}
        newLabel="Nova Ocorrência"
      >
        <select
          className="px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as StatusOcorrencia | "");
            setPage(1);
          }}
          aria-label="Filtrar por status"
        >
          <option value="">Todos os status</option>
          {Object.entries(STATUS_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </PageHeader>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      ) : ocorrencias.length === 0 ? (
        <Card>
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            Nenhuma ocorrência encontrada.
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {ocorrencias.map((o) => (
            <Card key={o.id} className="hover:shadow-md transition-shadow">
              <div
                role="button"
                tabIndex={0}
                className="cursor-pointer"
                onClick={() => setDetailId(o.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") setDetailId(o.id);
                }}
              >
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">{o.titulo}</h3>
                      <Badge variant={STATUS_VARIANT[o.status]}>{STATUS_LABEL[o.status]}</Badge>
                      <Badge variant={SEVERIDADE_VARIANT[o.severidade]}>
                        {o.severidade}
                      </Badge>
                      <Badge variant="default">{TIPO_LABEL[o.tipo]}</Badge>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-300 mt-2 line-clamp-2">
                      {o.descricao}
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      {o.aluno_nome ? `Aluno: ${o.aluno_nome}` : o.turma_codigo ? `Turma: ${o.turma_codigo}` : "Sem vínculo"}
                      {" · "}
                      {new Date(o.created_at).toLocaleString("pt-BR")}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
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

      {/* Criação */}
      <Modal
        open={showForm}
        title="Nova Ocorrência"
        onClose={() => setShowForm(false)}
        size="lg"
      >
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            criarMutation.mutate();
          }}
        >
          <Select
            label="Turma"
            value={form.turma_id}
            onChange={(e) => setForm((f) => ({ ...f, turma_id: e.target.value, aluno_id: "" }))}
            placeholder="Selecione a turma (opcional)"
            options={(turmas?.items ?? []).map((t) => ({ value: t.id, label: t.codigo }))}
          />
          {form.turma_id && (
            <Select
              label="Aluno"
              value={form.aluno_id}
              onChange={(e) => setForm((f) => ({ ...f, aluno_id: e.target.value }))}
              placeholder="Selecione o aluno (opcional)"
              options={(matriculas?.items ?? []).map((m) => ({
                value: m.aluno_id,
                label: m.aluno_nome,
              }))}
            />
          )}
          <Input
            label="Título"
            value={form.titulo}
            onChange={(e) => setForm((f) => ({ ...f, titulo: e.target.value }))}
            required
            minLength={3}
          />
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Descrição</label>
            <textarea
              className="w-full px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
              rows={4}
              value={form.descricao}
              onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
              required
              minLength={3}
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select
              label="Tipo"
              value={form.tipo}
              onChange={(e) => setForm((f) => ({ ...f, tipo: e.target.value as TipoOcorrencia }))}
              options={Object.entries(TIPO_LABEL).map(([value, label]) => ({ value, label }))}
            />
            <Select
              label="Severidade"
              value={form.severidade}
              onChange={(e) =>
                setForm((f) => ({ ...f, severidade: e.target.value as SeveridadeOcorrencia }))
              }
              options={[
                { value: "baixa", label: "Baixa" },
                { value: "media", label: "Média" },
                { value: "alta", label: "Alta" },
              ]}
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>
              Cancelar
            </Button>
            <Button type="submit" loading={criarMutation.isPending}>
              Registrar
            </Button>
          </div>
        </form>
      </Modal>

      {/* Detalhe */}
      <Modal
        open={!!detailId}
        title={detail?.ocorrencia.titulo ?? "Ocorrência"}
        onClose={() => setDetailId(null)}
        size="lg"
      >
        {detailLoading || !detail ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={STATUS_VARIANT[detail.ocorrencia.status]}>
                {STATUS_LABEL[detail.ocorrencia.status]}
              </Badge>
              <Badge variant={SEVERIDADE_VARIANT[detail.ocorrencia.severidade]}>
                {detail.ocorrencia.severidade}
              </Badge>
              <Badge variant="default">{TIPO_LABEL[detail.ocorrencia.tipo]}</Badge>
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {detail.ocorrencia.descricao}
            </p>

            {canManage && TRANSICOES[detail.ocorrencia.status].length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                {TRANSICOES[detail.ocorrencia.status].map((novo) => (
                  <Button
                    key={novo}
                    size="sm"
                    variant={novo === "arquivada" ? "secondary" : "primary"}
                    loading={statusMutation.isPending}
                    onClick={() =>
                      statusMutation.mutate({ id: detail.ocorrencia.id, status: novo })
                    }
                  >
                    {STATUS_LABEL[novo]}
                  </Button>
                ))}
              </div>
            )}

            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Histórico
              </h4>
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg divide-y divide-gray-200 dark:divide-gray-700 max-h-60 overflow-y-auto">
                {detail.historico.map((h) => (
                  <div key={h.id} className="px-3 py-2 text-sm">
                    <p className="text-gray-700 dark:text-gray-300">{h.acao}</p>
                    <p className="text-xs text-gray-400">
                      {new Date(h.created_at).toLocaleString("pt-BR")}
                      {h.status_novo ? ` · ${STATUS_LABEL[h.status_novo]}` : ""}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
