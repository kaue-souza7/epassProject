import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { seriesApi, type Serie } from "../../api/endpoints";
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

export function SeriesList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const [deactivateId, setDeactivateId] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;

  const { data: series, isLoading, isError } = useQuery({
    queryKey: ["series"],
    queryFn: () => seriesApi.list(),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => seriesApi.update(id, { ativo: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["series"] });
      toast("success", "Série desativada com sucesso");
      setDeactivateId(null);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao desativar série");
      setDeactivateId(null);
    },
  });

  const itemToDeactivate = deactivateId
    ? series?.find((s) => s.id === deactivateId)
    : null;

  const filtered = (series ?? []).filter((s) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      s.nome.toLowerCase().includes(q) ||
      String(s.numero).includes(q) ||
      (s.descricao?.toLowerCase() || "").includes(q)
    );
  });

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Séries" }]} />
        <PageHeader title="Séries" description="Gerencie as séries do sistema" />
        <Card>
          <ErrorState
            title="Erro ao carregar séries"
            message="Não foi possível carregar a lista de séries. Tente novamente."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["series"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Séries" }]} />
      <PageHeader
        title="Séries"
        description={`${filtered.length} série${filtered.length !== 1 ? "s" : ""}`}
        showNew={canWrite}
        onNew={() => navigate(`${prefix}/series/novo`)}
        newLabel="Nova Série"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            className="pl-9 pr-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 w-full sm:w-64"
            placeholder="Buscar por nome, número..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </PageHeader>

      <DataTable
        columns={[
          { key: "numero", header: "Nº" },
          { key: "nome", header: "Nome" },
          {
            key: "descricao",
            header: "Descrição",
            render: (item: Serie) => item.descricao || "—",
          },
          {
            key: "ativo",
            header: "Status",
            render: (item: Serie) => (
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
                  render: (item: Serie) => (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`${prefix}/series/${item.id}`);
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
        emptyMessage="Nenhuma série encontrada"
        onRowClick={
          canWrite
            ? (item) => navigate(`${prefix}/series/${item.id}`)
            : undefined
        }
      />

      <ConfirmDialog
        open={!!deactivateId}
        title="Desativar Série"
        message={`Tem certeza que deseja desativar a série "${itemToDeactivate?.nome}"?`}
        confirmLabel="Desativar"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateId && deactivateMutation.mutate(deactivateId)}
        onCancel={() => setDeactivateId(null)}
      />
    </div>
  );
}
