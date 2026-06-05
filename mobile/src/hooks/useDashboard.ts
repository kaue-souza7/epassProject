import { useApi } from "./useApi";
import { getDashboard } from "../api/dashboard.service";
import type { DashboardResponsavel } from "../types/responsavel";

interface UseDashboardResult {
  data: DashboardResponsavel | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useDashboard(): UseDashboardResult {
  const { data, loading, error, refetch } = useApi(
    (signal) => getDashboard(signal),
    [],
    { errorMessage: "Erro ao carregar dashboard" }
  );
  return { data, loading, error, refetch };
}
