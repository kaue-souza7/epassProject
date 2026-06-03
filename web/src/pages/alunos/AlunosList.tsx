import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { studentsApi, type Aluno } from "../../api/endpoints";
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

export function AlunosList() {
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
    queryKey: ["students", { nome: search || undefined, page }],
    queryFn: () => studentsApi.list({ nome: search || undefined, page, size: 20 }),
  });

  const alunos = data?.items;
  const pagination = data as PaginatedResponse<Aluno> | undefined;

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => studentsApi.update(id, { ativo: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students"] });
      toast("success", "Aluno desativado com sucesso");
      setDeactivateId(null);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao desativar aluno");
      setDeactivateId(null);
    },
  });

  const itemToDeactivate = deactivateId
    ? (alunos ?? []).find((a) => a.id === deactivateId)
    : null;

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Alunos" }]} />
        <PageHeader title="Alunos" description="Gerencie os alunos do sistema" />
        <Card>
          <ErrorState
            title="Erro ao carregar alunos"
            message="Não foi possível carregar a lista de alunos. Tente novamente."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["students"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Alunos" }]} />
      <PageHeader
        title="Alunos"
        description="Gerencie os alunos do sistema"
        showNew={canWrite}
        onNew={() => navigate(`${prefix}/alunos/novo`)}
        newLabel="Novo Aluno"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            aria-label="Buscar aluno por nome"
            className="pl-9 pr-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 w-full sm:w-64"
            placeholder="Buscar por nome..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
      </PageHeader>

      <DataTable
        columns={[
          { key: "nome", header: "Nome" },
          {
            key: "cpf",
            header: "CPF",
            render: (item: Aluno) => item.cpf || "—",
          },
          {
            key: "telefone",
            header: "Telefone",
            render: (item: Aluno) => item.telefone || "—",
          },
          {
            key: "email",
            header: "Email",
            render: (item: Aluno) => item.email || "—",
          },
          {
            key: "ativo",
            header: "Status",
            render: (item: Aluno) => (
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
                  render: (item: Aluno) => (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`${prefix}/alunos/${item.id}`);
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
        data={alunos ?? []}
        keyExtractor={(item) => item.id}
        loading={isLoading}
        emptyMessage="Nenhum aluno encontrado"
        onRowClick={
          canWrite
            ? (item) => navigate(`${prefix}/alunos/${item.id}`)
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
        title="Desativar Aluno"
        message={`Tem certeza que deseja desativar o aluno "${itemToDeactivate?.nome}"?`}
        confirmLabel="Desativar"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateId && deactivateMutation.mutate(deactivateId)}
        onCancel={() => setDeactivateId(null)}
      />
    </div>
  );
}
