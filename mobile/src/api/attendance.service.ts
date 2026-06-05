import { api } from "./client";

export interface ChamadaResponse {
  id: string;
  alocacao_id: string;
  data_hora_aula: string;
}

export interface FrequenciaComMatriculaResponse {
  id: string;
  chamada_id: string;
  matricula_id: string;
  matricula_codigo: string | null;
  aluno_nome: string | null;
  status: string;
  observacoes: string | null;
}

export interface ChamadaDetalheResponse {
  id: string;
  alocacao_id: string;
  data_hora_aula: string;
  frequencias: FrequenciaComMatriculaResponse[];
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export async function listCalls(
  alocacaoId: string,
  page = 1,
  size = 31
): Promise<PaginatedResponse<ChamadaResponse>> {
  const { data } = await api.get<PaginatedResponse<ChamadaResponse>>(
    "/attendance/calls",
    { params: { alocacao_id: alocacaoId, page, size } }
  );
  return data;
}

export async function getCall(
  id: string
): Promise<ChamadaDetalheResponse> {
  const { data } = await api.get<ChamadaDetalheResponse>(
    `/attendance/calls/${id}`
  );
  return data;
}

export interface FrequenciaResumo {
  matricula_id: string;
  aluno_id: string | null;
  aluno_nome: string | null;
  turma_codigo: string | null;
  frequencia_media: number | null;
  total_aulas: number;
  presencas: number;
  faltas: number;
  faltas_justificadas: number;
  situacao_hoje: string | null;
}

export async function getFrequencySummary(
  alunoId?: string,
  signal?: AbortSignal
): Promise<FrequenciaResumo> {
  const { data } = await api.get<FrequenciaResumo>(
    "/attendance/me/summary",
    { params: alunoId ? { aluno_id: alunoId } : undefined, signal }
  );
  return data;
}
