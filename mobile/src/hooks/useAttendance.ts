import { useApi } from "./useApi";
import { getFrequencySummary } from "../api/attendance.service";
import { useSelectedStudent } from "./useSelectedStudent";
import type { FrequenciaResumo } from "../api/attendance.service";

interface UseAttendanceResult {
  frequency: FrequenciaResumo | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useAttendance(): UseAttendanceResult {
  const { selectedChild } = useSelectedStudent();
  const alunoId = selectedChild?.aluno_id;

  const { data: frequency, loading, error, refetch } = useApi(
    (signal) => getFrequencySummary(alunoId, signal),
    [alunoId],
    { enabled: !!alunoId, errorMessage: "Erro ao carregar frequência" }
  );

  return { frequency, loading, error, refetch };
}
