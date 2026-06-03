import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { academicYearsApi, type AnoLetivo } from "../../api/endpoints";
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

export function AnosLetivosList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const [deactivateId, setDeactivateId] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const canWrite = user?.perfil && WRITE_ROLES.includes(user.perfil);
  const prefix = `/${user?.perfil}`;

  const { data: anosLetivos, isLoading, isError } = useQuery({
    queryKey: ["academic-years"],
    queryFn: academicYearsApi.list,
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => academicYearsApi.update(id, { ativo: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["academic-years"] });
      toast("success", "Ano letivo desativado com sucesso");
      setDeactivateId(null);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao desativar ano letivo");
      setDeactivateId(null);
    },
  });

  const itemToDeactivate = deactivateId
    ? anosLetivos?.find((a) => a.id === deactivateId)
    : null;

  const filtered = (anosLetivos ?? []).filter((a) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return String(a.ano).includes(q);
  });

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Anos Letivos" }]} />
        <PageHeader title="Anos Letivos" description="Gerencie os anos letivos do sistema" />
        <Card>
          <ErrorState
            title="Erro ao carregar anos letivos"
            message="Não foi possível carregar a lista de anos letivos. Tente novamente."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["academic-years"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Anos Letivos" }]} />
      <PageHeader
        title="Anos Letivos"
        description={`${filtered.length} ano${filtered.length !== 1 ? "s" : ""} letivo${filtered.length !== 1 ? "s" : ""}`}
        showNew={canWrite}
        onNew={() => navigate(`${prefix}/anos-letivos/novo`)}
        newLabel="Novo Ano Letivo"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            className="pl-9 pr-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 w-full sm:w-64"
            placeholder="Buscar por ano..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </PageHeader>

      <DataTable
        columns={[
          { key: "ano", header: "Ano" },
          {
            key: "data_inicio",
            header: "Data Início",
            render: (item: AnoLetivo) =>
              new Date(item.data_inicio).toLocaleDateString("pt-BR"),
          },
          {
            key: "data_fim",
            header: "Data Fim",
            render: (item: AnoLetivo) =>
              new Date(item.data_fim).toLocaleDateString("pt-BR"),
          },
          {
            key: "ativo",
            header: "Status",
            render: (item: AnoLetivo) => (
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
                  render: (item: AnoLetivo) => (
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`${prefix}/anos-letivos/${item.id}`);
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
        emptyMessage="Nenhum ano letivo encontrado"
          onRowClick={
            canWrite
              ? (item) => navigate(`${prefix}/anos-letivos/${item.id}`)
              : undefined
          }
      />

      <ConfirmDialog
        open={!!deactivateId}
        title="Desativar Ano Letivo"
        message={`Tem certeza que deseja desativar o ano letivo "${itemToDeactivate?.ano}"?`}
        confirmLabel="Desativar"
        loading={deactivateMutation.isPending}
        onConfirm={() => deactivateId && deactivateMutation.mutate(deactivateId)}
        onCancel={() => setDeactivateId(null)}
      />
    </div>
  );
}
