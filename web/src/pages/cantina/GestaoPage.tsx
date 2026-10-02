import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  DollarSign,
  ShoppingCart,
  Users,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Skeleton } from "../../components/ui/Skeleton";
import { EmptyState } from "../../components/ui/EmptyState";
import { useToast } from "../../components/ui/Toast";
import { api } from "../../api/client";

interface VendaPeriodo {
  data: string;
  vendas: number;
  quantidade: number;
}

interface ProdutoMaisVendido {
  produto_id: string;
  produto_nome: string;
  quantidade_vendida: number;
  receita_total: number;
}

interface AlertaEstoque {
  produto_id: string;
  produto_nome: string;
  estoque_atual: number;
  estoque_minimo: number;
  tipo: string;
}

interface UltimaVenda {
  id: string;
  aluno_nome: string;
  aluno_turma: string | null;
  valor_total: number;
  status: string;
  tipo: string;
  produtos: { nome: string | null; quantidade: number }[];
  created_at: string;
}

interface DashboardData {
  vendas_do_dia: number;
  quantidade_vendas: number;
  alunos_atendidos: number;
  produtos_estoque_baixo: number;
  vendas_por_periodo: VendaPeriodo[];
  produtos_mais_vendidos: ProdutoMaisVendido[];
  alertas_estoque: AlertaEstoque[];
  ultimas_vendas: UltimaVenda[];
}

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

const AUTO_REFRESH_INTERVAL = 30_000;

const STATUS_BADGE: Record<string, { variant: "success" | "warning" | "danger" | "info" | "default"; label: string }> = {
  pendente: { variant: "warning", label: "Pendente" },
  aprovado: { variant: "info", label: "Aprovado" },
  em_producao: { variant: "info", label: "Em Produção" },
  pronto: { variant: "success", label: "Pronto" },
  retirado: { variant: "default", label: "Retirado" },
  cancelado: { variant: "danger", label: "Cancelado" },
};

function SkeletonKpi() {
  return (
    <Card className="text-center">
      <div className="flex flex-col items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-full" />
        <Skeleton className="h-8 w-24" />
        <Skeleton className="h-4 w-28" />
      </div>
    </Card>
  );
}

function SkeletonChart({ height = 300 }: { height?: number }) {
  return (
    <Card>
      <Skeleton className="h-5 w-48 mb-4" />
      <div style={{ height }} className="w-full">
        <Skeleton className="w-full h-full rounded-lg" />
      </div>
    </Card>
  );
}

function GestaoDashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-7 w-56 mb-2" />
        <Skeleton className="h-4 w-72" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonKpi key={i} />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <SkeletonChart height={320} />
        <div className="lg:col-span-1">
          <SkeletonChart height={320} />
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkeletonChart height={200} />
        <SkeletonChart height={200} />
      </div>
    </div>
  );
}

export function GestaoPage() {
  const { toast } = useToast();
  const [dias, setDias] = useState(7);

  const fetchDashboard = useCallback(async () => {
    const res = await api.get<DashboardData>("/cantina/dashboard", {
      params: { dias },
    });
    return res.data;
  }, [dias]);

  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ["cantina-dashboard", dias],
    queryFn: fetchDashboard,
    refetchInterval: AUTO_REFRESH_INTERVAL,
    retry: 1,
  });

  useEffect(() => {
    if (error) {
      toast("error", "Erro ao carregar dados da cantina");
    }
  }, [error, toast]);

  const now = new Date();
  const todayFormatted = now.toLocaleDateString("pt-BR", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const vendasPeriodo = (data?.vendas_por_periodo || []).map((v) => ({
    ...v,
    label: shortDate(v.data),
  }));

  const produtosTop = (data?.produtos_mais_vendidos || []).slice(0, 8);

  return (
    <div className="space-y-6">
      <Breadcrumb items={[{ label: "Cantina" }, { label: "Gestão" }]} />

      <PageHeader
        title="Gestão da Cantina"
        description={`Painel de vendas e operações — ${todayFormatted}`}
      >
        <div className="flex items-center gap-2">
          <select
            value={dias}
            onChange={(e) => setDias(Number(e.target.value))}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value={7}>Últimos 7 dias</option>
            <option value={15}>Últimos 15 dias</option>
            <option value={30}>Últimos 30 dias</option>
          </select>
          <Button
            variant="ghost"
            onClick={() => refetch()}
            loading={isFetching}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </PageHeader>

      {isLoading ? (
        <GestaoDashboardSkeleton />
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <div className="flex items-center gap-4">
                <div className="flex-shrink-0 h-12 w-12 rounded-full bg-success-100 dark:bg-success-900/30 flex items-center justify-center">
                  <DollarSign className="h-6 w-6 text-success-600 dark:text-success-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {formatCurrency(data?.vendas_do_dia ?? 0)}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Vendas do Dia
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-4">
                <div className="flex-shrink-0 h-12 w-12 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                  <ShoppingCart className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {data?.quantidade_vendas ?? 0}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Quantidade de Vendas
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-4">
                <div className="flex-shrink-0 h-12 w-12 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                  <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {data?.alunos_atendidos ?? 0}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Alunos Atendidos
                  </p>
                </div>
              </div>
            </Card>

            <Card>
              <div className="flex items-center gap-4">
                <div className="flex-shrink-0 h-12 w-12 rounded-full bg-danger-100 dark:bg-danger-900/30 flex items-center justify-center">
                  <AlertTriangle className="h-6 w-6 text-danger-600 dark:text-danger-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {data?.produtos_estoque_baixo ?? 0}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Estoque Baixo
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Vendas por Período */}
            <Card className="lg:col-span-2">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Vendas por Período
              </h2>
              {vendasPeriodo.length === 0 ? (
                <EmptyState
                  title="Sem dados de vendas"
                  description="Nenhum registro de venda no período selecionado."
                />
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={vendasPeriodo}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 12 }}
                      stroke="#9ca3af"
                    />
                    <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
                    <Tooltip
                      formatter={(value: number, name: string) =>
                        name === "vendas"
                          ? formatCurrency(value)
                          : value
                      }
                      labelFormatter={(label) => `Data: ${label}`}
                      contentStyle={{
                        borderRadius: "8px",
                        border: "1px solid #e5e7eb",
                        fontSize: 12,
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="vendas"
                      stroke="#FF5B8F"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                      name="vendas"
                    />
                    <Line
                      type="monotone"
                      dataKey="quantidade"
                      stroke="#2ECC71"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                      name="quantidade"
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Card>

            {/* Produtos Mais Vendidos */}
            <Card>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Produtos Mais Vendidos
              </h2>
              {produtosTop.length === 0 ? (
                <EmptyState
                  title="Sem dados"
                  description="Nenhuma venda registrada no período."
                />
              ) : (
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={produtosTop} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                    <YAxis
                      type="category"
                      dataKey="produto_nome"
                      tick={{ fontSize: 11 }}
                      width={100}
                      stroke="#9ca3af"
                    />
                    <Tooltip
                      formatter={(value: number, name: string) =>
                        name === "receita_total"
                          ? formatCurrency(value)
                          : value
                      }
                      contentStyle={{
                        borderRadius: "8px",
                        border: "1px solid #e5e7eb",
                        fontSize: 12,
                      }}
                    />
                    <Bar
                      dataKey="quantidade_vendida"
                      fill="#FF5B8F"
                      radius={[0, 4, 4, 0]}
                      name="quantidade"
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>

          {/* Alerts and Recent Sales */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Alertas de Estoque */}
            <Card>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Alertas de Estoque
              </h2>
              {(!data?.alertas_estoque || data.alertas_estoque.length === 0) ? (
                <EmptyState
                  icon={AlertTriangle}
                  title="Sem alertas"
                  description="Todos os produtos estoque ok."
                />
              ) : (
                <div className="space-y-3">
                  {data.alertas_estoque.map((alerta) => (
                    <div
                      key={alerta.produto_id}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {alerta.produto_nome}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Estoque: {alerta.estoque_atual} / Mínimo:{" "}
                          {alerta.estoque_minimo}
                        </p>
                      </div>
                      <Badge
                        variant={
                          alerta.estoque_atual === 0 ? "danger" : "warning"
                        }
                      >
                        {alerta.estoque_atual === 0
                          ? "Sem Estoque"
                          : "Estoque Baixo"}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Últimas Vendas */}
            <Card>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Últimas Vendas
              </h2>
              {(!data?.ultimas_vendas || data.ultimas_vendas.length === 0) ? (
                <EmptyState
                  title="Nenhuma venda registrada"
                  description="As vendas aparecerão aqui."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                        <th className="pb-2">Aluno</th>
                        <th className="pb-2">Produtos</th>
                        <th className="pb-2">Valor</th>
                        <th className="pb-2">Status</th>
                        <th className="pb-2">Tipo</th>
                        <th className="pb-2">Data/Hora</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.ultimas_vendas.map((venda) => {
                        const statusInfo = STATUS_BADGE[venda.status] || {
                          variant: "default" as const,
                          label: venda.status,
                        };
                        return (
                          <tr
                            key={venda.id}
                            className="border-b dark:border-gray-700/50"
                          >
                            <td className="py-2">
                              <div>
                                <p className="font-medium text-gray-900 dark:text-gray-100">
                                  {venda.aluno_nome}
                                </p>
                                {venda.aluno_turma && (
                                  <p className="text-xs text-gray-500 dark:text-gray-400">
                                    {venda.aluno_turma}
                                  </p>
                                )}
                              </div>
                            </td>
                            <td className="py-2 text-xs text-gray-700 dark:text-gray-300 max-w-[200px] truncate">
                              {venda.produtos && venda.produtos.length > 0
                                ? venda.produtos.map((p) => `${p.nome} x${p.quantidade}`).join(", ")
                                : "—"}
                            </td>
                            <td className="py-2 font-medium text-gray-900 dark:text-gray-100">
                              {formatCurrency(venda.valor_total)}
                            </td>
                            <td className="py-2">
                              <Badge variant={statusInfo.variant}>
                                {statusInfo.label}
                              </Badge>
                            </td>
                            <td className="py-2 text-gray-700 dark:text-gray-300">
                              {venda.tipo === "consumo_direto"
                                ? "Consumo Direto"
                                : "Pedido"}
                            </td>
                            <td className="py-2 text-gray-500 dark:text-gray-400 text-xs">
                              {formatDateTime(venda.created_at)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
