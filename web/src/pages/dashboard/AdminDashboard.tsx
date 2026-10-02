import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { useAuth } from "../../contexts/AuthContext";
import { Card } from "../../components/ui/Card";
import { StatCard } from "../../components/ui/StatCard";
import { ErrorState } from "../../components/ui/ErrorState";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonDashboard } from "../../components/ui/SkeletonDashboard";
import { Stagger, StaggerItem } from "../../components/motion";
import { dashboardApi } from "../../api/endpoints";
import { logger } from "../../lib/logger";
import type { AdminDashboardResponse } from "../../api/endpoints";
import { School, Users, GraduationCap, FilePlus, BadgeCheck, Layers, ClipboardList } from "lucide-react";

export function AdminDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<AdminDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await dashboardApi.admin();
      setData(result);
    } catch (err: any) {
      const msg = err?.response?.data?.message || err?.message || "Erro ao carregar dashboard";
      logger.error("AdminDashboard fetch failed", { error: msg });
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
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard Administrativo</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Bem-vindo, {user?.nome}</p>
        </div>
        <Card>
          <ErrorState title="Erro ao carregar dashboard" message={error} onRetry={fetchData} />
        </Card>
      </div>
    );
  }

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Dashboard Administrativo</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Bem-vindo, {user?.nome}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          index={0}
          icon={Users}
          label="Alunos Ativos"
          value={data?.cards.total_alunos_ativos}
        />
        <StatCard
          index={1}
          icon={BadgeCheck}
          label="Professores Ativos"
          value={data?.cards.total_professores_ativos}
          tone="info"
        />
        <StatCard
          index={2}
          icon={Layers}
          label="Turmas Ativas"
          value={data?.cards.total_turmas_ativas}
          tone="success"
        />
        <StatCard
          index={3}
          icon={ClipboardList}
          label="Matrículas Ativas"
          value={data?.cards.total_matriculas_ativas}
          tone="warning"
        />
      </div>

      <Stagger className="grid grid-cols-1 lg:grid-cols-2 gap-6" interval={0.09}>
        <StaggerItem>
          <Card className="h-full">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Últimas Matrículas</h2>
            {data?.ultimas_matriculas?.length ? (
              <div className="overflow-x-auto epass-scrollbar">
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
                    {data.ultimas_matriculas.map((m) => (
                      <tr
                        key={m.id}
                        className="border-b dark:border-gray-700/50 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/30"
                      >
                        <td className="py-2">{m.aluno_nome}</td>
                        <td className="py-2">{m.turma_codigo}</td>
                        <td className="py-2">{new Date(m.data_matricula).toLocaleDateString()}</td>
                        <td className="py-2 capitalize">{m.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon={FilePlus} title="Nenhuma matrícula encontrada" />
            )}
          </Card>
        </StaggerItem>

        <StaggerItem>
          <Card className="h-full">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Últimas Alocações</h2>
            {data?.ultimas_alocacoes?.length ? (
              <div className="overflow-x-auto epass-scrollbar">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                      <th className="pb-2">Professor</th>
                      <th className="pb-2">Turma</th>
                      <th className="pb-2">Disciplina</th>
                      <th className="pb-2">Início</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.ultimas_alocacoes.map((a) => (
                      <tr
                        key={a.id}
                        className="border-b dark:border-gray-700/50 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/30"
                      >
                        <td className="py-2">{a.professor_nome}</td>
                        <td className="py-2">{a.turma_codigo}</td>
                        <td className="py-2">{a.disciplina_nome}</td>
                        <td className="py-2">{new Date(a.data_inicio).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon={Users} title="Nenhuma alocação encontrada" />
            )}
          </Card>
        </StaggerItem>
      </Stagger>

      <Stagger className="grid grid-cols-1 lg:grid-cols-2 gap-6" interval={0.09}>
        <StaggerItem>
          <Card className="h-full">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Top 10 — Ocupação de Turmas</h2>
            {data?.top_ocupacao?.length ? (
              <div className="overflow-x-auto epass-scrollbar">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                      <th className="pb-2">#</th>
                      <th className="pb-2">Turma</th>
                      <th className="pb-2">Vagas</th>
                      <th className="pb-2">Matrículas</th>
                      <th className="pb-2">Ocupação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_ocupacao.map((t, i) => (
                      <tr
                        key={t.turma_id}
                        className="border-b dark:border-gray-700/50 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/30"
                      >
                        <td className="py-2">{i + 1}</td>
                        <td className="py-2">{t.turma_codigo}</td>
                        <td className="py-2">{t.vagas_total}</td>
                        <td className="py-2">{t.matriculas_ativas}</td>
                        <td className="py-2">
                          <span className="font-medium">{t.taxa_ocupacao}%</span>
                          <span className="mt-1 block h-1.5 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                            <motion.span
                              className="block h-full rounded-full bg-gradient-to-r from-primary-500 to-accent-500"
                              initial={{ scaleX: 0 }}
                              animate={{ scaleX: Math.min(1, (t.taxa_ocupacao ?? 0) / 100) }}
                              transition={{ duration: 0.8, delay: 0.1 + i * 0.05, ease: [0.16, 1, 0.3, 1] }}
                              style={{ originX: 0 }}
                            />
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon={School} title="Nenhuma turma encontrada" />
            )}
          </Card>
        </StaggerItem>

        <StaggerItem>
          <Card className="h-full">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Alunos por Série</h2>
            {data?.alunos_por_serie?.length ? (
              <div className="overflow-x-auto epass-scrollbar">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                      <th className="pb-2">Série</th>
                      <th className="pb-2">Quantidade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.alunos_por_serie.map((s) => (
                      <tr
                        key={s.serie_id}
                        className="border-b dark:border-gray-700/50 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/30"
                      >
                        <td className="py-2">{s.serie_nome}</td>
                        <td className="py-2 font-medium">{s.quantidade}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon={GraduationCap} title="Nenhuma série encontrada" />
            )}
          </Card>
        </StaggerItem>
      </Stagger>
    </motion.div>
  );
}
