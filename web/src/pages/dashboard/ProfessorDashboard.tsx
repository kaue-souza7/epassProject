import { useEffect, useState, useCallback } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { Card } from "../../components/ui/Card";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonDashboard } from "../../components/ui/SkeletonDashboard";
import { dashboardApi } from "../../api/endpoints";
import { logger } from "../../lib/logger";
import type { ProfessorDashboardResponse } from "../../api/endpoints";
import { FileText, ClipboardList } from "lucide-react";

export function ProfessorDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<ProfessorDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await dashboardApi.professor();
      setData(result);
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.message || "Erro ao carregar dashboard";
      logger.error("ProfessorDashboard fetch failed", { error: msg });
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard do Professor</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Bem-vindo, {user?.nome}</p>
        </div>
        <Card>
          <ErrorState title="Erro ao carregar dashboard" message={error} onRetry={fetchData} />
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard do Professor</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Bem-vindo, {user?.nome}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">{data?.cards.minhas_turmas ?? "—"}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Minhas Turmas</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">{data?.cards.minhas_disciplinas ?? "—"}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Minhas Disciplinas</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">{data?.cards.chamadas_realizadas ?? "—"}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Chamadas Realizadas</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">{data?.cards.avaliacoes_cadastradas ?? "—"}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Avaliações</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Próximas Avaliações</h2>
          {data?.proximas_avaliacoes?.length ? (
            <>
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                      <th className="pb-2 pr-2">Título</th>
                      <th className="pb-2 pr-2">Disciplina</th>
                      <th className="pb-2 pr-2">Turma</th>
                      <th className="pb-2 pr-2">Data</th>
                      <th className="pb-2">Bimestre</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.proximas_avaliacoes.map((a) => (
                      <tr key={a.id} className="border-b dark:border-gray-700/50">
                        <td className="py-2 pr-2 whitespace-nowrap">{a.titulo}</td>
                        <td className="py-2 pr-2 whitespace-nowrap">{a.disciplina_nome}</td>
                        <td className="py-2 pr-2 whitespace-nowrap">{a.turma_codigo}</td>
                        <td className="py-2 pr-2 whitespace-nowrap">{new Date(a.data_aplicacao).toLocaleDateString()}</td>
                        <td className="py-2 whitespace-nowrap">{a.bimestre}°</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="md:hidden space-y-3">
                {data.proximas_avaliacoes.map((a) => (
                  <div key={a.id} className="flex items-center justify-between py-2 border-b dark:border-gray-700/50 last:border-0">
                    <div className="min-w-0 flex-1 mr-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{a.titulo}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{a.disciplina_nome} • {a.turma_codigo}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-xs text-gray-700 dark:text-gray-300">{new Date(a.data_aplicacao).toLocaleDateString()}</p>
                      <p className="text-xs text-gray-400">{a.bimestre}º Bim.</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <EmptyState icon={FileText} title="Nenhuma avaliação futura" />
          )}
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Últimas Chamadas</h2>
          {data?.ultimas_chamadas?.length ? (
            <>
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                      <th className="pb-2 pr-2">Disciplina</th>
                      <th className="pb-2 pr-2">Turma</th>
                      <th className="pb-2">Data/Hora</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.ultimas_chamadas.map((c) => (
                      <tr key={c.id} className="border-b dark:border-gray-700/50">
                        <td className="py-2 pr-2 whitespace-nowrap">{c.disciplina_nome}</td>
                        <td className="py-2 pr-2 whitespace-nowrap">{c.turma_codigo}</td>
                        <td className="py-2 whitespace-nowrap">{new Date(c.data_hora_aula).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="md:hidden space-y-3">
                {data.ultimas_chamadas.map((c) => (
                  <div key={c.id} className="flex items-center justify-between py-2 border-b dark:border-gray-700/50 last:border-0">
                    <div className="min-w-0 flex-1 mr-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{c.disciplina_nome}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{c.turma_codigo}</p>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0">{new Date(c.data_hora_aula).toLocaleString()}</p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <EmptyState icon={ClipboardList} title="Nenhuma chamada encontrada" />
          )}
        </Card>
      </div>
    </div>
  );
}
