import { useState, useEffect, useCallback } from "react";
import { getDashboard } from "../api/dashboard.service";
import type { DashboardResponsavel } from "../types/responsavel";

interface UseDashboardResult {
  data: DashboardResponsavel | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useDashboard(): UseDashboardResult {
  const [data, setData] = useState<DashboardResponsavel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDashboard();
      setData(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Erro ao carregar dashboard";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}
