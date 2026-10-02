import { api } from "./client";

export interface ProfessorTurma {
  alocacao_id: string;
  turma_id: string;
  turma_codigo: string;
  turma_nome: string | null;
  disciplina_id: string;
  disciplina_nome: string;
  serie_nome: string;
  ano_letivo: number;
  turno: string;
  total_alunos: number;
}

export interface ProfessorAluno {
  matricula_id: string;
  aluno_id: string;
  aluno_nome: string;
  numero_chamada: number | null;
}

export interface ProfessorAvaliacao {
  id: string;
  alocacao_id: string;
  titulo: string;
  tipo: string;
  peso: number;
  nota_maxima: number;
  bimestre: number;
  data_aplicacao: string;
}

export interface AssessmentGrade {
  id: string;
  avaliacao_id: string;
  matricula_id: string;
  aluno_nome: string | null;
  valor: number;
  observacoes: string | null;
}

export interface AssessmentGradesResponse {
  avaliacao: ProfessorAvaliacao;
  notas: AssessmentGrade[];
}

export interface FrequenciaSalvarItem {
  matricula_id: string;
  presente: boolean;
}

export interface NotaSalvarItem {
  matricula_id: string;
  valor: number;
}

export async function getProfessorTurmas(): Promise<ProfessorTurma[]> {
  const { data } = await api.get<ProfessorTurma[]>("/professor/turmas");
  return data;
}

export async function getTurmaAlunos(
  turmaId: string
): Promise<ProfessorAluno[]> {
  const { data } = await api.get<ProfessorAluno[]>(
    `/professor/turmas/${turmaId}/alunos`
  );
  return data;
}

export async function getProfessorAvaliacoes(
  alocacaoId: string,
  bimestre?: number
): Promise<ProfessorAvaliacao[]> {
  const params: Record<string, string | number> = { alocacao_id: alocacaoId };
  if (bimestre !== undefined) params.bimestre = bimestre;
  const { data } = await api.get<ProfessorAvaliacao[]>(
    "/professor/avaliacoes",
    { params }
  );
  return data;
}

export async function saveFrequencia(
  turmaId: string,
  dataStr: string,
  frequencias: FrequenciaSalvarItem[]
): Promise<{ chamada_id: string; message: string }> {
  const { data: response } = await api.post<{
    chamada_id: string;
    message: string;
  }>("/professor/frequencia", {
    turma_id: turmaId,
    data: dataStr,
    frequencias,
  });
  return response;
}

export async function getAssessmentGrades(
  avaliacaoId: string,
  signal?: AbortSignal
): Promise<AssessmentGradesResponse> {
  const { data } = await api.get<AssessmentGradesResponse>(
    `/assessments/${avaliacaoId}/grades`,
    { signal }
  );
  return data;
}

export async function saveNotas(
  avaliacaoId: string,
  notas: NotaSalvarItem[]
): Promise<{ message: string }> {
  const { data: response } = await api.post<{ message: string }>(
    "/professor/notas",
    {
      avaliacao_id: avaliacaoId,
      notas,
    }
  );
  return response;
}

// Boletim Liberação
export interface DisciplinaLiberacaoStatus {
  disciplina_id: string;
  disciplina_nome: string;
  liberada: boolean;
  liberado_em: string | null;
}

export interface LiberacaoStatusResponse {
  turma_id: string;
  turma_codigo: string;
  bimestre: number;
  ano_letivo_id: string;
  total_disciplinas_professor: number;
  disciplinas_liberadas: DisciplinaLiberacaoStatus[];
  todas_liberadas: boolean;
}

export interface LiberacaoBoletimResponse {
  id: string;
  professor_id: string;
  turma_id: string;
  disciplina_id: string;
  disciplina_nome: string;
  alocacao_id: string;
  ano_letivo_id: string;
  bimestre: number;
  liberado_em: string;
  ativo: boolean;
}

export async function liberarBoletim(
  turmaId: string,
  bimestre: number
): Promise<LiberacaoBoletimResponse[]> {
  const { data } = await api.post<LiberacaoBoletimResponse[]>(
    "/boletim-liberacao",
    { turma_id: turmaId, bimestre }
  );
  return data;
}

export async function getLiberacaoStatus(
  turmaId: string,
  bimestre: number
): Promise<LiberacaoStatusResponse> {
  const { data } = await api.get<LiberacaoStatusResponse>(
    "/boletim-liberacao/status",
    { params: { turma_id: turmaId, bimestre } }
  );
  return data;
}
