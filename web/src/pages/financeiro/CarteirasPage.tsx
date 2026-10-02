import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { financialApi, type WalletDetail } from "../../api/endpoints";
import { useToast } from "../../components/ui/Toast";
import { PageHeader } from "../../components/layout/PageHeader";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { DataTable } from "../../components/ui/DataTable";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ConfirmDialog } from "../../components/ui/ConfirmDialog";
import { ErrorState } from "../../components/ui/ErrorState";
import { Lock, Unlock } from "lucide-react";

const STATUS_LABEL: Record<string, string> = {
  ativa: "Ativa",
  bloqueada: "Bloqueada",
  cancelada: "Cancelada",
};

const STATUS_VARIANT: Record<string, "success" | "danger" | "default"> = {
  ativa: "success",
  bloqueada: "danger",
  cancelada: "default",
};

function formatBRL(valor: string | number): string {
  const n = typeof valor === "string" ? parseFloat(valor) : valor;
  return (Number.isFinite(n) ? n : 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export function CarteirasPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [confirm, setConfirm] = useState<{
    wallet: WalletDetail;
    acao: "block" | "unblock";
  } | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["wallets", statusFilter, page],
    queryFn: () =>
      financialApi.listWallets({
        status: statusFilter || undefined,
        page,
        size: 20,
      }),
  });

  const mutation = useMutation({
    mutationFn: ({ wallet, acao }: { wallet: WalletDetail; acao: "block" | "unblock" }) =>
      acao === "block"
        ? financialApi.blockWallet(wallet.id)
        : financialApi.unblockWallet(wallet.id),
    onSuccess: (_, vars) => {
      toast(
        "success",
        vars.acao === "block" ? "Carteira bloqueada" : "Carteira desbloqueada",
      );
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      setConfirm(null);
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao atualizar carteira");
      setConfirm(null);
    },
  });

  const wallets = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Carteiras" }]} />
        <Card>
          <ErrorState
            title="Erro ao carregar carteiras"
            message="Não foi possível carregar as carteiras."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["wallets"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Financeiro" }, { label: "Carteiras" }]} />
      <PageHeader
        title="Carteiras"
        description={`${total} carteira${total !== 1 ? "s" : ""}`}
        showNew={false}
      >
        <select
          className="px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          aria-label="Filtrar por status"
        >
          <option value="">Todos os status</option>
          <option value="ativa">Ativas</option>
          <option value="bloqueada">Bloqueadas</option>
          <option value="cancelada">Canceladas</option>
        </select>
      </PageHeader>

      <DataTable
        columns={[
          {
            key: "aluno_nome",
            header: "Aluno",
            render: (w: WalletDetail) => w.aluno_nome ?? w.aluno_id,
          },
          {
            key: "saldo",
            header: "Saldo",
            render: (w: WalletDetail) => formatBRL(w.saldo),
          },
          {
            key: "status",
            header: "Status",
            render: (w: WalletDetail) => (
              <Badge variant={STATUS_VARIANT[w.status] ?? "default"}>
                {STATUS_LABEL[w.status] ?? w.status}
              </Badge>
            ),
          },
          {
            key: "created_at",
            header: "Criada em",
            render: (w: WalletDetail) =>
              new Date(w.created_at).toLocaleDateString("pt-BR"),
          },
          {
            key: "acoes",
            header: "Ações",
            render: (w: WalletDetail) =>
              w.status === "cancelada" ? (
                <span className="text-xs text-gray-400">—</span>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setConfirm({ wallet: w, acao: w.status === "ativa" ? "block" : "unblock" })}
                >
                  {w.status === "ativa" ? (
                    <>
                      <Lock className="h-4 w-4 mr-1 text-danger-500" /> Bloquear
                    </>
                  ) : (
                    <>
                      <Unlock className="h-4 w-4 mr-1 text-success-500" /> Desbloquear
                    </>
                  )}
                </Button>
              ),
          },
        ]}
        data={wallets}
        keyExtractor={(w) => w.id}
        loading={isLoading}
        emptyMessage="Nenhuma carteira encontrada"
      />

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

      <ConfirmDialog
        open={!!confirm}
        title={confirm?.acao === "block" ? "Bloquear carteira" : "Desbloquear carteira"}
        message={
          confirm?.acao === "block"
            ? `Bloquear a carteira de ${confirm?.wallet.aluno_nome ?? "aluno"}? Consumos e pedidos serão recusados até o desbloqueio.`
            : `Desbloquear a carteira de ${confirm?.wallet.aluno_nome ?? "aluno"}?`
        }
        confirmLabel={confirm?.acao === "block" ? "Bloquear" : "Desbloquear"}
        loading={mutation.isPending}
        onConfirm={() => confirm && mutation.mutate(confirm)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
