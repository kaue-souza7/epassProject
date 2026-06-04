import { useState, useEffect, useCallback } from "react";
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
  const [reportCard, setReportCard] = useState<ReportCard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!enrollmentId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getReportCard(enrollmentId, bimestre);
      setReportCard(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Erro ao carregar boletim";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [enrollmentId, bimestre]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { reportCard, loading, error, refetch: fetch };
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
  const [annualReport, setAnnualReport] = useState<ReportCardAnnual | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!enrollmentId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getAnnualReport(enrollmentId);
      setAnnualReport(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Erro ao carregar boletim anual";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [enrollmentId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { annualReport, loading, error, refetch: fetch };
}
