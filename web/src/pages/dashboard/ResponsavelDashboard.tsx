import { useEffect, useState, useCallback } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { Card } from "../../components/ui/Card";
import { StatCard } from "../../components/ui/StatCard";
import { Badge } from "../../components/ui/Badge";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonDashboard } from "../../components/ui/SkeletonDashboard";
import { dashboardApi } from "../../api/endpoints";
import { logger } from "../../lib/logger";
import type { ResponsavelDashboardResponse } from "../../api/endpoints";
import {
  UserCheck,
  School,
  TrendingUp,
  TrendingDown,
  Users,
  ClipboardList,
  GraduationCap,
  Percent,
} from "lucide-react";

export function ResponsavelDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<ResponsavelDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await dashboardApi.responsavel();
      setData(result);
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.message || "Erro ao carregar dashboard";
      logger.error("ResponsavelDashboard fetch failed", { error: msg });
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) return <SkeletonDashboard />;

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard Familiar</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Bem-vindo, {user?.nome}</p>
        </div>
        <Card>
          <ErrorState title="Erro ao carregar dashboard" message={error} onRetry={fetchData} />
        </Card>
      </div>
    );
  }

  const situacaoBadge = (situacao: string | undefined | null) => {
    if (situacao === "aprovado") return <Badge variant="success">Aprovado</Badge>;
    if (situacao === "reprovado") return <Badge variant="danger">Reprovado</Badge>;
    if (situacao === "recuperacao") return <Badge variant="warning">Em Recuperação</Badge>;
    if (situacao === "aprovado_pos_recuperacao") return <Badge variant="success">Aprovado (Pós-Recuperação)</Badge>;
    if (situacao === "reprovado_pos_recuperacao") return <Badge variant="danger">Reprovado (Pós-Recuperação)</Badge>;
    return <Badge variant="default">—</Badge>;
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard Familiar</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Bem-vindo, {user?.nome}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          index={0}
          icon={Users}
          label="Filhos"
          value={data?.cards.quantidade_filhos}
        />
        <StatCard
          index={1}
          icon={ClipboardList}
          label="Matrículas Ativas"
          value={data?.cards.matriculas_ativas}
          tone="info"
        />
        <StatCard
          index={2}
          icon={GraduationCap}
          label="Média Geral"
          value={data?.cards.media_geral}
          tone="success"
          decimals={1}
        />
        <StatCard
          index={3}
          icon={Percent}
          label="Frequência Média"
          value={
            data?.cards.frequencia_media != null
              ? `${data.cards.frequencia_media}%`
              : undefined
          }
          tone="success"
        />
      </div>

      <Card>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Filhos</h2>
        {data?.filhos?.length ? (
          <>
            <div className="space-y-3 md:hidden">
              {data.filhos.map((f) => (
                <div key={f.aluno_id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <UserCheck className="h-5 w-5 text-primary-500 flex-shrink-0" />
                      <span className="font-medium text-gray-900 dark:text-gray-100 truncate">{f.aluno_nome}</span>
                    </div>
                    {situacaoBadge(f.situacao)}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
                      <School className="h-4 w-4 flex-shrink-0" />
                      <span>{f.turma_codigo ?? "—"}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
                      <TrendingUp className="h-4 w-4 flex-shrink-0" />
                      <span>Média: {f.media_geral ?? "—"}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 col-span-2">
                      <TrendingDown className="h-4 w-4 flex-shrink-0" />
                      <span>Frequência: {f.frequencia_media != null ? `${f.frequencia_media}%` : "—"}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                    <th className="pb-2">Nome</th>
                    <th className="pb-2">Turma</th>
                    <th className="pb-2">Média</th>
                    <th className="pb-2">Frequência</th>
                    <th className="pb-2">Situação</th>
                  </tr>
                </thead>
                <tbody>
                  {data.filhos.map((f) => (
                    <tr key={f.aluno_id} className="border-b dark:border-gray-700/50">
                      <td className="py-2">{f.aluno_nome}</td>
                      <td className="py-2">{f.turma_codigo ?? "—"}</td>
                      <td className="py-2">{f.media_geral ?? "—"}</td>
                      <td className="py-2">{f.frequencia_media != null ? `${f.frequencia_media}%` : "—"}</td>
                      <td className="py-2">{situacaoBadge(f.situacao)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <EmptyState icon={Users} title="Nenhum filho encontrado" />
        )}
      </Card>
    </div>
  );
}
