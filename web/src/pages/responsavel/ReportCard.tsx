import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { studentsApi, reportsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { SkeletonReportCard } from "../../components/ui/SkeletonReportCard";
import { Button } from "../../components/ui/Button";
import {
  ArrowLeft,
  School,
  GraduationCap,
  Calendar,
  BookOpen,
  Percent,
  BarChart3,
  Printer,
} from "lucide-react";
import { ErrorState } from "../../components/ui/ErrorState";

const BIMESTRES = [1, 2, 3, 4];

const situacaoBadge: Record<string, "success" | "warning" | "danger" | "info"> = {
  aprovado: "success",
  reprovado: "danger",
  recuperacao: "warning",
  aprovado_pos_recuperacao: "success",
  reprovado_pos_recuperacao: "danger",
  cursando: "info",
};

const situacaoLabel: Record<string, string> = {
  aprovado: "Aprovado",
  reprovado: "Reprovado",
  recuperacao: "Em Recuperação",
  aprovado_pos_recuperacao: "Aprovado (Pós-Recuperação)",
  reprovado_pos_recuperacao: "Reprovado (Pós-Recuperação)",
  cursando: "Cursando",
};

export function ReportCard() {
  const { childId, enrollmentId } = useParams<{ childId?: string; enrollmentId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const prefix = `/${user?.perfil}`;
  const [bimestre, setBimestre] = useState(1);

  const { data: allChildren } = useQuery({
    queryKey: ["my-children"],
    queryFn: studentsApi.myChildren,
    enabled: !!childId,
  });
  const child = allChildren?.find((c) => c.id === childId);

  const { data: report, isLoading, isError } = useQuery({
    queryKey: ["report-card", enrollmentId, bimestre],
    queryFn: () => reportsApi.boletimBimestral(enrollmentId!, bimestre),
    enabled: !!enrollmentId,
  });

  const { data: annualReport } = useQuery({
    queryKey: ["report-card-annual", enrollmentId],
    queryFn: () => reportsApi.boletimAnual(enrollmentId!),
    enabled: !!enrollmentId,
  });

  const mediaGeral = report?.disciplinas.length
    ? report.disciplinas.reduce((acc, d) => acc + Number(d.media), 0) / report.disciplinas.length
    : null;

  const freqGeral = report?.disciplinas.length
    ? (() => {
        const withFreq = report.disciplinas.filter((d) => d.frequencia !== null && d.frequencia !== undefined);
        return withFreq.length
          ? withFreq.reduce((acc, d) => acc + (d.frequencia ?? 0), 0) / withFreq.length
          : null;
      })()
    : null;

  const hasAnnualReport = annualReport?.situacao_final && annualReport.situacao_final !== "cursando";

  const queryClient = useQueryClient();

  const isProfessorFlow = !childId;
  const breadcrumbItems = isProfessorFlow
    ? [
        { label: "Boletins", path: `${prefix}/boletins` },
        { label: "Boletim" },
      ]
    : [
        { label: "Meus Filhos", path: `${prefix}/meus-filhos` },
        { label: child?.nome ?? "Detalhes", path: `${prefix}/meus-filhos/${childId}` },
        { label: "Boletim" },
      ];

  const backPath = isProfessorFlow
    ? `${prefix}/boletins`
    : `${prefix}/meus-filhos/${childId}`;

  if (isLoading) {
    return (
      <div>
        <div className="no-print">
          <Breadcrumb items={breadcrumbItems} />
        </div>
        <SkeletonReportCard />
      </div>
    );
  }

  if (isError || !report) {
    return (
      <div>
        <div className="no-print">
          <Breadcrumb items={breadcrumbItems} />
        </div>
        <Card>
          <ErrorState
            title="Erro ao carregar boletim"
            message="Não foi possível carregar o boletim do aluno."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["report-card", enrollmentId, bimestre] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <div className="no-print">
        <Breadcrumb items={[
          ...breadcrumbItems.slice(0, -1),
          { label: `Boletim - ${bimestre}º Bimestre` },
        ]} />
      </div>

      <div className="flex items-center gap-4 mb-6 no-print">
        <button
          className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors flex-shrink-0"
          onClick={() => navigate(backPath)}
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 truncate">Boletim Escolar</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{report.aluno_nome}</p>
        </div>
        <Button variant="outline" onClick={() => window.print()} className="flex-shrink-0">
          <Printer className="h-4 w-4 mr-2" />
          Imprimir Boletim
        </Button>
      </div>

      <Card className="mb-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          <div className="flex items-center gap-2 md:gap-3">
            <School className="h-5 w-5 text-primary-500 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-gray-500 dark:text-gray-400">Turma</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{report.turma_codigo}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 md:gap-3">
            <GraduationCap className="h-5 w-5 text-primary-500 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-gray-500 dark:text-gray-400">Série</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{report.serie_nome}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 md:gap-3">
            <Calendar className="h-5 w-5 text-primary-500 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-gray-500 dark:text-gray-400">Ano Letivo</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{report.ano_letivo}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 md:gap-3">
            <BookOpen className="h-5 w-5 text-primary-500 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-gray-500 dark:text-gray-400">Bimestre</p>
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{report.bimestre}º Bimestre</p>
            </div>
          </div>
        </div>
      </Card>

      <div className="flex items-center gap-2 mb-6 no-print">
        <span className="text-sm text-gray-500 dark:text-gray-400 hidden sm:inline">Bimestre:</span>
        <div className="flex gap-1">
          {BIMESTRES.map((b) => (
            <Button
              key={b}
              variant={bimestre === b ? "primary" : "outline"}
              size="sm"
              onClick={() => setBimestre(b)}
            >
              {b}º
            </Button>
          ))}
        </div>
      </div>

      <Card padding="none" className="overflow-hidden mb-6">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
                <th className="text-left px-4 md:px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Disciplina</th>
                <th className="text-center px-4 md:px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Média</th>
                <th className="text-center px-4 md:px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Frequência</th>
                {annualReport?.media_pre_recuperacao != null && (
                  <th className="text-center px-4 md:px-6 py-3 font-medium text-gray-600 dark:text-gray-400">Recuperação</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {report.disciplinas.map((d) => (
                <tr key={d.disciplina_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-4 md:px-6 py-3 text-gray-900 dark:text-gray-100 font-medium">
                    {d.disciplina_nome}
                    {d.situacao === "recuperacao" && (
                      <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400">
                        Em Rec.
                      </span>
                    )}
                  </td>
                  <td className="px-4 md:px-6 py-3 text-center text-gray-700 dark:text-gray-300">
                    {Number(d.media).toFixed(1)}
                  </td>
                  <td className="px-4 md:px-6 py-3 text-center">
                    {d.frequencia !== null && d.frequencia !== undefined ? (
                      <span className={d.frequencia < 75 ? "text-danger-500 font-medium" : "text-gray-700 dark:text-gray-300"}>
                        {d.frequencia.toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  {annualReport?.media_pre_recuperacao != null && (
                    <td className="px-4 md:px-6 py-3 text-center">
                      {d.nota_recuperacao != null ? (
                        <span className="tabular-nums text-primary-600 dark:text-primary-400 font-medium">
                          {Number(d.nota_recuperacao).toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="mb-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary-500 flex-shrink-0" />
          <span className="truncate">Resumo do {bimestre}º Bimestre</span>
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
          <div className="flex items-center gap-3 p-3 md:p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <BarChart3 className="h-6 w-6 md:h-8 md:w-8 text-primary-500 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-gray-500 dark:text-gray-400">Média Geral</p>
              <p className="text-base md:text-lg font-bold text-gray-900 dark:text-gray-100">
                {mediaGeral !== null ? mediaGeral.toFixed(1) : "—"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 md:p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <Percent className="h-6 w-6 md:h-8 md:w-8 text-primary-500 flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-xs text-gray-500 dark:text-gray-400">Frequência Geral</p>
              <p className="text-base md:text-lg font-bold text-gray-900 dark:text-gray-100">
                {freqGeral !== null ? `${freqGeral.toFixed(1)}%` : "—"}
              </p>
            </div>
          </div>
        </div>
      </Card>

      {hasAnnualReport && (
        <Card>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary-500 flex-shrink-0" />
            Situação Final
          </h2>
          <div className="flex items-center gap-3 mb-3">
            <Badge variant={situacaoBadge[annualReport.situacao_final] ?? "default"}>
              {situacaoLabel[annualReport.situacao_final] ?? annualReport.situacao_final}
            </Badge>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Ano letivo {report.ano_letivo}
            </span>
          </div>
          {annualReport.media_pre_recuperacao != null && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="text-sm">
                <span className="text-gray-500 dark:text-gray-400">Média pré-recuperação: </span>
                <span className="font-medium text-gray-900 dark:text-gray-100">{Number(annualReport.media_pre_recuperacao).toFixed(1)}</span>
              </div>
              {annualReport.media_pos_recuperacao != null && (
                <div className="text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Média pós-recuperação: </span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{Number(annualReport.media_pos_recuperacao).toFixed(1)}</span>
                </div>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
