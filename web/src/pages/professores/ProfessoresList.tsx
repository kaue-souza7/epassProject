import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { teachersApi, type Professor } from "../../api/endpoints";
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

const WRITE_ROLES = ["admin", "secretaria"];

export function ProfessoresList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const [deactivateId, setDeactivateId] = useState<string | null>(null);
  const [searchNome, setSearchNome] = useState("");
  const [page, setPage] = useState(1);

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["teachers", { nome: searchNome, page }],
    queryFn: () => teachersApi.list({ nome: searchNome || undefined, page, size: 10 }),
  });

  const deactivateMutation = useMutation({
    mutationFn: (usuario_id: string) => teachersApi.update(usuario_id, { ativo: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teachers"] });
      toast("success", "Professor desativado com sucesso");
      setDeactivateId(null);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao desativar professor");
      setDeactivateId(null);
    },
  });

  const itemToDeactivate = deactivateId
    ? data?.items.find((p) => p.usuario_id === deactivateId)
    : null;

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Professores" }]} />
        <PageHeader title="Professores" description="Gerencie os professores do sistema" />
        <Card>
          <ErrorState
            title="Erro ao carregar professores"
            message="Não foi possível carregar a lista de professores. Tente novamente."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["teachers"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Professores" }]} />
      <PageHeader
        title="Professores"
        description="Gerencie os professores do sistema"
        showNew={canWrite}
        onNew={() => navigate(`${prefix}/professores/novo`)}
        newLabel="Novo Professor"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            aria-label="Buscar professor por nome"
            className="pl-9 pr-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 w-full sm:w-64"
            placeholder="Buscar por nome..."
            value={searchNome}
            onChange={(e) => {
              setSearchNome(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </PageHeader>

      <DataTable
        columns={[
          {
            key: "nome",
            header: "Nome",
            render: (item: Professor) => (item as any).nome || item.usuario_id,
          },
          {
            key: "matricula_funcional",
            header: "Matrícula",
            render: (item: Professor) => item.matricula_funcional || "—",
          },
          {
            key: "formacao_principal",
            header: "Formação",
            render: (item: Professor) => item.formacao_principal || "—",
          },
          {
            key: "ativo",
            header: "Status",
            render: (item: Professor) => (
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
                  render: (item: Professor) => (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`${prefix}/professores/${item.usuario_id}`);
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
                            setDeactivateId(item.usuario_id);
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
        data={data?.items ?? []}
        keyExtractor={(item) => item.usuario_id}
        loading={isLoading}
        emptyMessage="Nenhum professor encontrado"
        onRowClick={
          canWrite
            ? (item) => navigate(`${prefix}/professores/${item.usuario_id}`)
            : undefined
        }
      />

      {data && data.pages > 1 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mt-4 text-sm text-gray-500 dark:text-gray-400">
          <span className="text-center sm:text-left">Página {data.page} de {data.pages} ({data.total} registros)</span>
          <div className="flex gap-2 justify-center sm:justify-end">
            <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Anterior
            </Button>
            <Button variant="ghost" size="sm" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>
              Próxima
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deactivateId}
        title="Desativar Professor"
        message={`Tem certeza que deseja desativar o professor "${itemToDeactivate ? (itemToDeactivate as any).nome || itemToDeactivate.usuario_id : ""}"?`}
        confirmLabel="Desativar"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateId && deactivateMutation.mutate(deactivateId)}
        onCancel={() => setDeactivateId(null)}
      />
    </div>
  );
}
