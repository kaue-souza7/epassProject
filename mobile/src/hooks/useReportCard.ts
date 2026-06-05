import { useApi } from "./useApi";
import { getReportCard, getAnnualReport } from "../api/report.service";
import type { ReportCard, ReportCardAnnual } from "../types/responsavel";

interface UseReportCardResult {
  reportCard: ReportCard | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useReportCard(
  enrollmentId: string | null,
  bimestre: number
): UseReportCardResult {
  const { data: reportCard, loading, error, refetch } = useApi(
    (signal) => getReportCard(enrollmentId!, bimestre, signal),
    [enrollmentId, bimestre],
    { enabled: !!enrollmentId, errorMessage: "Erro ao carregar boletim" }
  );

  return { reportCard, loading, error, refetch };
}

interface UseAnnualReportResult {
  annualReport: ReportCardAnnual | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useAnnualReport(
  enrollmentId: string | null
): UseAnnualReportResult {
  const { data: annualReport, loading, error, refetch } = useApi(
    (signal) => getAnnualReport(enrollmentId!, signal),
    [enrollmentId],
    { enabled: !!enrollmentId, errorMessage: "Erro ao carregar boletim anual" }
  );

  return { annualReport, loading, error, refetch };
}
