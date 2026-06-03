import { useEffect, useState, useCallback } from "react";
import { useAuth } from "../../contexts/AuthContext";
import { Card } from "../../components/ui/Card";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonDashboard } from "../../components/ui/SkeletonDashboard";
import { dashboardApi } from "../../api/endpoints";
import { logger } from "../../lib/logger";
import type { SecretariaDashboardResponse } from "../../api/endpoints";
import { FilePlus, School } from "lucide-react";

export function SecretariaDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<SecretariaDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await dashboardApi.secretaria();
      setData(result);
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.message || "Erro ao carregar dashboard";
      logger.error("SecretariaDashboard fetch failed", { error: msg });
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard Operacional</h1>
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard Operacional</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Bem-vindo, {user?.nome}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">{data?.cards.matriculas_ativas ?? "—"}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Matrículas Ativas</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">{data?.cards.matriculas_ano ?? "—"}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Matrículas no Ano</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-500">{data?.cards.turmas_ativas ?? "—"}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Turmas Ativas</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-danger-500">{data?.cards.alunos_sem_matricula ?? "—"}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Alunos sem Matrícula</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Matrículas Recentes</h2>
          {data?.matriculas_recentes?.length ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                  <th className="pb-2">Aluno</th>
                  <th className="pb-2">Turma</th>
                  <th className="pb-2">Data</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.matriculas_recentes.map((m) => (
                  <tr key={m.id} className="border-b dark:border-gray-700/50">
                    <td className="py-2">{m.aluno_nome}</td>
                    <td className="py-2">{m.turma_codigo}</td>
                    <td className="py-2">{new Date(m.data_matricula).toLocaleDateString()}</td>
                    <td className="py-2 capitalize">{m.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState icon={FilePlus} title="Nenhuma matrícula recente" />
          )}
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Turmas com Vagas Esgotadas</h2>
          {data?.turmas_lotadas?.length ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                  <th className="pb-2">Turma</th>
                  <th className="pb-2">Vagas</th>
                  <th className="pb-2">Matrículas</th>
                </tr>
              </thead>
              <tbody>
                {data.turmas_lotadas.map((t) => (
                  <tr key={t.turma_id} className="border-b dark:border-gray-700/50">
                    <td className="py-2">{t.turma_codigo}</td>
                    <td className="py-2">{t.vagas_total}</td>
                    <td className="py-2 font-medium">{t.matriculas_ativas}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState icon={School} title="Nenhuma turma lotada" />
          )}
        </Card>
      </div>
    </div>
  );
}
