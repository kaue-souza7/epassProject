import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { classesApi, seriesApi, type Turma } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { PageHeader } from "../../components/layout/PageHeader";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { DataTable } from "../../components/ui/DataTable";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { Pencil, Trash2, Search } from "lucide-react";
import { ErrorState } from "../../components/ui/ErrorState";
import type { PaginatedResponse } from "../../types/api";

const WRITE_ROLES = ["admin", "secretaria"];

export function TurmasList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const [deactivateId, setDeactivateId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["classes", { page }],
    queryFn: () => classesApi.list({ page, size: 20 }),
  });

  const turmas = data?.items;
  const pagination = data as PaginatedResponse<Turma> | undefined;

  const { data: series } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
  });

  const serieMap = new Map(series?.map((s) => [s.id, s]) ?? []);

  const turnoLabel: Record<string, string> = {
    manha: "Manhã",
    tarde: "Tarde",
    noite: "Noite",
  };

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => classesApi.update(id, { ativo: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["classes"] });
      toast("success", "Turma desativada com sucesso");
      setDeactivateId(null);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao desativar turma");
      setDeactivateId(null);
    },
  });

  const itemToDeactivate = deactivateId
    ? turmas?.find((t) => t.id === deactivateId)
    : null;

  const filtered = (turmas ?? []).filter((t) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      t.codigo.toLowerCase().includes(q) ||
      (t.nome?.toLowerCase() || "").includes(q) ||
      (serieMap.get(t.serie_id)?.nome?.toLowerCase() || "").includes(q) ||
      (turnoLabel[t.turno] || t.turno).toLowerCase().includes(q)
    );
  });

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Turmas" }]} />
        <PageHeader title="Turmas" description="Gerencie as turmas do sistema" />
        <Card>
          <ErrorState
            title="Erro ao carregar turmas"
            message="Não foi possível carregar a lista de turmas. Tente novamente."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["classes"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Turmas" }]} />
      <PageHeader
        title="Turmas"
        description={`${filtered.length} turma${filtered.length !== 1 ? "s" : ""}`}
        showNew={canWrite}
        onNew={() => navigate(`${prefix}/turmas/novo`)}
        newLabel="Nova Turma"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            aria-label="Buscar turma"
            className="pl-9 pr-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 w-full sm:w-64"
            placeholder="Buscar por código, nome, série..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
      </PageHeader>

      <DataTable
        columns={[
          { key: "codigo", header: "Código" },
          {
            key: "nome",
            header: "Nome",
            render: (item: Turma) => item.nome || "—",
          },
          {
            key: "serie_id",
            header: "Série",
            render: (item: Turma) => serieMap.get(item.serie_id)?.nome ?? "—",
          },
          {
            key: "turno",
            header: "Turno",
            render: (item: Turma) => turnoLabel[item.turno] || item.turno,
          },
          {
            key: "vagas_total",
            header: "Vagas",
          },
          {
            key: "ativo",
            header: "Status",
            render: (item: Turma) => (
              <Badge variant={item.ativo ? "success" : "danger"}>
                {item.ativo ? "Ativo" : "Inativo"}
              </Badge>
            ),
          },
          ...(canWrite
            ? [
                {
                  key: "acoes" as string,
                  header: "Ações",
                  render: (item: Turma) => (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`${prefix}/turmas/${item.id}`);
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      {item.ativo && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeactivateId(item.id);
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-danger-500" />
                        </Button>
                      )}
                    </div>
                  ),
                } as any,
              ]
            : []),
        ]}
        data={filtered}
        keyExtractor={(item) => item.id}
        loading={isLoading}
        emptyMessage="Nenhuma turma encontrada"
        onRowClick={
          canWrite
            ? (item) => navigate(`${prefix}/turmas/${item.id}`)
            : undefined
        }
      />

      {pagination && pagination.pages > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-4 text-sm text-gray-500 dark:text-gray-400">
          <span className="text-center sm:text-left">Página {pagination.page} de {pagination.pages} ({pagination.total} registros)</span>
          <div className="flex gap-2 justify-center sm:justify-end">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </Button>
            <Button variant="ghost" size="sm" disabled={page >= pagination.pages} onClick={() => setPage((p) => p + 1)}>
              Próxima
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deactivateId}
        title="Desativar Turma"
        message={`Tem certeza que deseja desativar a turma "${itemToDeactivate?.codigo}"?`}
        confirmLabel="Desativar"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateId && deactivateMutation.mutate(deactivateId)}
        onCancel={() => setDeactivateId(null)}
      />
    </div>
  );
}
