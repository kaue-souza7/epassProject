import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { subjectsApi, type Disciplina } from "../../api/endpoints";
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

const WRITE_ROLES = ["admin"];

export function DisciplinasList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const [deactivateId, setDeactivateId] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;

  const { data: disciplinas, isLoading, isError } = useQuery({
    queryKey: ["subjects"],
    queryFn: () => subjectsApi.list(),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => subjectsApi.update(id, { ativo: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subjects"] });
      toast("success", "Disciplina desativada com sucesso");
      setDeactivateId(null);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao desativar disciplina");
      setDeactivateId(null);
    },
  });

  const itemToDeactivate = deactivateId
    ? disciplinas?.find((d) => d.id === deactivateId)
    : null;

  const filtered = (disciplinas ?? []).filter((d) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      d.codigo.toLowerCase().includes(q) ||
      d.nome.toLowerCase().includes(q) ||
      (d.descricao?.toLowerCase() || "").includes(q)
    );
  });

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Disciplinas" }]} />
        <PageHeader title="Disciplinas" description="Gerencie as disciplinas do sistema" />
        <Card>
          <ErrorState
            title="Erro ao carregar disciplinas"
            message="Não foi possível carregar a lista de disciplinas. Tente novamente."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["subjects"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Disciplinas" }]} />
      <PageHeader
        title="Disciplinas"
        description={`${filtered.length} disciplina${filtered.length !== 1 ? "s" : ""}`}
        showNew={canWrite}
        onNew={() => navigate(`${prefix}/disciplinas/novo`)}
        newLabel="Nova Disciplina"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            className="pl-9 pr-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 w-full sm:w-64"
            placeholder="Buscar por código, nome..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </PageHeader>

      <DataTable
        columns={[
          { key: "codigo", header: "Código" },
          { key: "nome", header: "Nome" },
          {
            key: "descricao",
            header: "Descrição",
            render: (item: Disciplina) => item.descricao || "—",
          },
          {
            key: "ativo",
            header: "Status",
            render: (item: Disciplina) => (
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
                  render: (item: Disciplina) => (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`${prefix}/disciplinas/${item.id}`);
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
        emptyMessage="Nenhuma disciplina encontrada"
        onRowClick={
          canWrite
            ? (item) => navigate(`${prefix}/disciplinas/${item.id}`)
            : undefined
        }
      />

      <ConfirmDialog
        open={!!deactivateId}
        title="Desativar Disciplina"
        message={`Tem certeza que deseja desativar a disciplina "${itemToDeactivate?.nome}"?`}
        confirmLabel="Desativar"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateId && deactivateMutation.mutate(deactivateId)}
        onCancel={() => setDeactivateId(null)}
      />
    </div>
  );
}
