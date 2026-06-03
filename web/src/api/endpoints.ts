import { api } from "./client";
import type { PaginatedResponse } from "../types/api";

export interface AnoLetivo {
  id: string;
  ano: number;
  data_inicio: string;
  data_fim: string;
  ativo: boolean;
}

export interface Serie {
  id: string;
  numero: number;
  nome: string;
  descricao: string | null;
  ativo: boolean;
}

export interface Disciplina {
  id: string;
  codigo: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
}

export interface Professor {
  usuario_id: string;
  nome: string;
  formacao_principal: string | null;
  matricula_funcional: string | null;
  data_contratacao: string | null;
  observacoes: string | null;
  ativo: boolean;
}

export interface Aluno {
  id: string;
  nome: string;
  data_nascimento: string;
  cpf: string | null;
  rg: string | null;
  endereco: string | null;
  telefone: string | null;
  email: string | null;
  data_entrada: string;
  ativo: boolean;
}

export interface Turma {
  id: string;
  codigo: string;
  nome: string | null;
  serie_id: string;
  ano_letivo_id: string;
  turno: string;
  vagas_total: number;
  ativo: boolean;
}

function paginatedGet<T>(url: string, params?: Record<string, any>) {
  return api.get<PaginatedResponse<T>>(url, { params }).then((r) => r.data);
}

function listAll<T>(url: string, params?: Record<string, any>) {
  return api.get<T[]>(url, { params }).then((r) => r.data);
}

function getById<T>(url: string) {
  return api.get<T>(url).then((r) => r.data);
}

function create<T>(url: string, data: any) {
  return api.post<T>(url, data).then((r) => r.data);
}

function update<T>(url: string, data: any) {
  return api.put<T>(url, data).then((r) => r.data);
}

export const academicYearsApi = {
  list: () => listAll<AnoLetivo>("/academic-years"),
  getById: (id: string) => getById<AnoLetivo>(`/academic-years/${id}`),
  create: (data: Partial<AnoLetivo>) => create<AnoLetivo>("/academic-years", data),
  update: (id: string, data: Partial<AnoLetivo>) => update<AnoLetivo>(`/academic-years/${id}`, data),
};

export const seriesApi = {
  list: (only_active?: boolean) => listAll<Serie>("/series", { only_active }),
  getById: (id: string) => getById<Serie>(`/series/${id}`),
  create: (data: Partial<Serie>) => create<Serie>("/series", data),
  update: (id: string, data: Partial<Serie>) => update<Serie>(`/series/${id}`, data),
};

export const subjectsApi = {
  list: (only_active?: boolean) => listAll<Disciplina>("/subjects", { only_active }),
  getById: (id: string) => getById<Disciplina>(`/subjects/${id}`),
  create: (data: Partial<Disciplina>) => create<Disciplina>("/subjects", data),
  update: (id: string, data: Partial<Disciplina>) => update<Disciplina>(`/subjects/${id}`, data),
};

export const teachersApi = {
  list: (params?: { nome?: string; matricula_funcional?: string; only_active?: boolean; page?: number; size?: number }) =>
    paginatedGet<Professor>("/teachers", params),
  getById: (usuario_id: string) => getById<Professor>(`/teachers/${usuario_id}`),
  create: (data: Partial<Professor>) => create<Professor>("/teachers", data),
  update: (usuario_id: string, data: Partial<Professor>) => update<Professor>(`/teachers/${usuario_id}`, data),
};

export interface MyChildrenItem {
  id: string;
  nome: string;
  ativo: boolean;
}

export interface HistoricoItem {
  matricula_id: string;
  ano_letivo: number;
  turma_codigo: string;
  serie_nome: string;
  data_matricula: string;
  data_saida: string | null;
  status: string;
  situacao_final: string | null;
  media_final: number | null;
  frequencia_final: number | null;
}

export interface HistoricoEscolarResponse {
  aluno_id: string;
  aluno_nome: string;
  historico: HistoricoItem[];
}

export const studentsApi = {
  list: (params?: { nome?: string; only_active?: boolean; page?: number; size?: number }) =>
    paginatedGet<Aluno>("/students", params),
  getById: (id: string) => getById<Aluno>(`/students/${id}`),
  create: (data: Partial<Aluno>) => create<Aluno>("/students", data),
  update: (id: string, data: Partial<Aluno>) => update<Aluno>(`/students/${id}`, data),
  myChildren: () => listAll<MyChildrenItem>("/students/my-children"),
  getHistory: (id: string) => getById<HistoricoEscolarResponse>(`/students/${id}/history`),
};

export interface EnrollmentsListResponse {
  id: string;
  aluno_id: string;
  aluno_nome: string;
  turma_id: string;
  turma_codigo: string;
  matricula_origem_id: string | null;
  data_matricula: string;
  status: string;
  data_saida: string | null;
  motivo_saida: string | null;
  observacoes: string | null;
}

export interface EnrollmentResponse {
  id: string;
  aluno_id: string;
  turma_id: string;
  matricula_origem_id: string | null;
  data_matricula: string;
  status: string;
  data_saida: string | null;
  motivo_saida: string | null;
  observacoes: string | null;
}

export const enrollmentsApi = {
  list: (params?: { aluno_id?: string; turma_id?: string; status?: string; page?: number; size?: number }) =>
    paginatedGet<EnrollmentsListResponse>("/enrollments", params),
  getById: (id: string) => getById<EnrollmentResponse>(`/enrollments/${id}`),
  create: (data: { aluno_id: string; turma_id: string; observacoes?: string | null }) =>
    create<EnrollmentResponse>("/enrollments", data),
};

export const classesApi = {
  list: (params?: { only_active?: boolean; page?: number; size?: number }) =>
    paginatedGet<Turma>("/classes", params),
  getById: (id: string) => getById<Turma>(`/classes/${id}`),
  create: (data: Partial<Turma>) => create<Turma>("/classes", data),
  update: (id: string, data: Partial<Turma>) => update<Turma>(`/classes/${id}`, data),
};

export interface AllocationResponse {
  id: string;
  professor_id: string;
  turma_id: string;
  disciplina_id: string;
  data_inicio: string;
  data_fim: string | null;
}

export const allocationsApi = {
  list: (params?: { turma_id?: string; professor_id?: string; only_active?: boolean; page?: number; size?: number }) =>
    paginatedGet<AllocationResponse>("/allocations", params),
  getById: (id: string) => getById<AllocationResponse>(`/allocations/${id}`),
  create: (data: { professor_id: string; turma_id: string; disciplina_id: string; data_inicio?: string | null }) =>
    create<AllocationResponse>("/allocations", data),
  encerrar: (id: string, data: { data_fim: string }) =>
    update<AllocationResponse>(`/allocations/${id}`, data),
};

export interface ChamadaResponse {
  id: string;
  alocacao_id: string;
  data_hora_aula: string;
}

export interface ChamadaDetalheResponse {
  id: string;
  alocacao_id: string;
  data_hora_aula: string;
  frequencias: FrequenciaComMatriculaResponse[];
}

export interface FrequenciaComMatriculaResponse {
  id: string;
  chamada_id: string;
  matricula_id: string;
  matricula_codigo: string | null;
  aluno_nome: string | null;
  status: StatusFrequencia;
  observacoes: string | null;
}

export type StatusFrequencia = "presente" | "falta" | "falta_justificada";

export interface FrequenciaRegistrar {
  matricula_id: string;
  status: StatusFrequencia;
  observacoes?: string | null;
}

export type TipoAvaliacao = "prova" | "trabalho" | "atividade" | "recuperacao" | "simulado" | "outro";

export interface AvaliacaoResponse {
  id: string;
  alocacao_id: string;
  titulo: string;
  tipo: TipoAvaliacao;
  peso: number;
  nota_maxima: number;
  bimestre: number;
  data_aplicacao: string;
  observacoes: string | null;
}

export interface AvaliacaoCreate {
  alocacao_id: string;
  titulo: string;
  tipo: TipoAvaliacao;
  peso: number;
  nota_maxima?: number;
  bimestre: number;
  data_aplicacao: string;
  observacoes?: string | null;
}

export interface AvaliacaoUpdate {
  titulo?: string;
  data_aplicacao?: string;
  observacoes?: string | null;
}

export interface NotaComAlunoResponse {
  id: string;
  avaliacao_id: string;
  matricula_id: string;
  aluno_nome: string | null;
  valor: number;
  observacoes: string | null;
}

export interface AvaliacaoGradesResponse {
  avaliacao: AvaliacaoResponse;
  notas: NotaComAlunoResponse[];
}

export interface NotaLancar {
  matricula_id: string;
  valor: number;
  observacoes?: string | null;
}

export const assessmentsApi = {
  list: (params: { alocacao_id: string; bimestre?: number; page?: number; size?: number }) =>
    paginatedGet<AvaliacaoResponse>("/assessments", params),
  getById: (id: string) => getById<AvaliacaoResponse>(`/assessments/${id}`),
  getGrades: (id: string) => getById<AvaliacaoGradesResponse>(`/assessments/${id}/grades`),
  create: (data: AvaliacaoCreate) => create<AvaliacaoResponse>("/assessments", data),
  update: (id: string, data: AvaliacaoUpdate) => update<AvaliacaoResponse>(`/assessments/${id}`, data),
  launchGrades: (avaliacao_id: string, notas: NotaLancar[]) =>
    api.post<NotaComAlunoResponse[]>("/assessments/grades", { avaliacao_id, notas }).then((r) => r.data),
};

export interface DisciplinaBoletim {
  disciplina_id: string;
  disciplina_nome: string;
  nota_maxima: number;
  media: number;
  frequencia: number | null;
  nota_recuperacao: number | null;
  media_pos_recuperacao: number | null;
  situacao: string | null;
}

export interface BoletimBimestral {
  matricula_id: string;
  aluno_nome: string;
  turma_codigo: string;
  serie_nome: string;
  ano_letivo: number;
  bimestre: number;
  disciplinas: DisciplinaBoletim[];
}

export interface BoletimAnual {
  matricula_id: string;
  aluno_nome: string;
  turma_codigo: string;
  serie_nome: string;
  ano_letivo: number;
  bimestres: BoletimBimestral[];
  situacao_final: string;
  media_pre_recuperacao: number | null;
  media_pos_recuperacao: number | null;
}

export const reportsApi = {
  boletimBimestral: (enrollmentId: string, bimestre: number) =>
    api.get<BoletimBimestral>(`/reports/report-card/${enrollmentId}`, { params: { bimestre } }).then((r) => r.data),
  boletimAnual: (enrollmentId: string) =>
    api.get<BoletimAnual>(`/reports/report-card/${enrollmentId}/annual`).then((r) => r.data),
};

export interface AdminCards {
  total_alunos_ativos: number;
  total_professores_ativos: number;
  total_turmas_ativas: number;
  total_matriculas_ativas: number;
}

export interface MatriculaResumo {
  id: string;
  aluno_nome: string;
  turma_codigo: string;
  data_matricula: string;
  status: string;
}

export interface AlocacaoResumo {
  id: string;
  professor_nome: string;
  turma_codigo: string;
  disciplina_nome: string;
  data_inicio: string;
}

export interface OcupacaoTurma {
  turma_id: string;
  turma_codigo: string;
  vagas_total: number;
  matriculas_ativas: number;
  taxa_ocupacao: number;
}

export interface AlunosPorSerie {
  serie_id: string;
  serie_nome: string;
  quantidade: number;
}

export interface AdminDashboardResponse {
  cards: AdminCards;
  ultimas_matriculas: MatriculaResumo[];
  ultimas_alocacoes: AlocacaoResumo[];
  top_ocupacao: OcupacaoTurma[];
  alunos_por_serie: AlunosPorSerie[];
}

export interface SecretariaCards {
  matriculas_ativas: number;
  matriculas_ano: number;
  turmas_ativas: number;
  alunos_sem_matricula: number;
}

export interface TurmaLotada {
  turma_id: string;
  turma_codigo: string;
  vagas_total: number;
  matriculas_ativas: number;
}

export interface SecretariaDashboardResponse {
  cards: SecretariaCards;
  matriculas_recentes: MatriculaResumo[];
  turmas_lotadas: TurmaLotada[];
}

export interface ProfessorCards {
  minhas_turmas: number;
  minhas_disciplinas: number;
  chamadas_realizadas: number;
  avaliacoes_cadastradas: number;
}

export interface AvaliacaoResumo {
  id: string;
  titulo: string;
  disciplina_nome: string;
  turma_codigo: string;
  data_aplicacao: string;
  bimestre: number;
}

export interface ChamadaResumo {
  id: string;
  disciplina_nome: string;
  turma_codigo: string;
  data_hora_aula: string;
}

export interface ProfessorDashboardResponse {
  cards: ProfessorCards;
  proximas_avaliacoes: AvaliacaoResumo[];
  ultimas_chamadas: ChamadaResumo[];
}

export interface ResponsavelCards {
  quantidade_filhos: number;
  matriculas_ativas: number;
  media_geral: number | null;
  frequencia_media: number | null;
}

export interface FilhoResumo {
  aluno_id: string;
  aluno_nome: string;
  matricula_id: string | null;
  turma_codigo: string | null;
  situacao: string | null;
  media_geral: number | null;
  frequencia_media: number | null;
}

export interface ResponsavelDashboardResponse {
  cards: ResponsavelCards;
  filhos: FilhoResumo[];
}

export const dashboardApi = {
  admin: () => api.get<AdminDashboardResponse>("/dashboard/admin").then((r) => r.data),
  secretaria: () => api.get<SecretariaDashboardResponse>("/dashboard/secretaria").then((r) => r.data),
  professor: () => api.get<ProfessorDashboardResponse>("/dashboard/professor").then((r) => r.data),
  responsavel: () => api.get<ResponsavelDashboardResponse>("/dashboard/responsavel").then((r) => r.data),
};

export interface ConfiguracaoAcademicaResponse {
  id: string;
  ano_letivo_id: string;
  media_aprovacao: number;
  frequencia_minima: number;
  possui_recuperacao: boolean;
  media_minima_recuperacao: number | null;
  quantidade_periodos: number;
  ativo: boolean;
}

export const academicConfigApi = {
  get: (anoLetivoId: string) => getById<ConfiguracaoAcademicaResponse>(`/academic-config/${anoLetivoId}`),
  update: (anoLetivoId: string, data: Partial<ConfiguracaoAcademicaResponse>) =>
    update<ConfiguracaoAcademicaResponse>(`/academic-config/${anoLetivoId}`, data),
};

export const attendanceApi = {
  listCalls: (alocacao_id: string, page?: number, size?: number) =>
    paginatedGet<ChamadaResponse>("/attendance/calls", { alocacao_id, page, size }),
  getCall: (id: string) => getById<ChamadaDetalheResponse>(`/attendance/calls/${id}`),
  createCall: (data: { alocacao_id: string; data_hora_aula: string }) =>
    create<ChamadaResponse>("/attendance/calls", data),
  registerFrequencies: (chamada_id: string, frequencias: FrequenciaRegistrar[]) =>
    api.post("/attendance/frequencies", { chamada_id, frequencias }),
};

// Agenda Events
export type TipoDestinoEvento = "professor" | "responsavel" | "turma";

export interface EventoDestinatarioCreate {
  tipo_destino: TipoDestinoEvento;
  destino_id: string;
}

export interface EventoDestinatarioResponse {
  id: string;
  evento_id: string;
  tipo_destino: TipoDestinoEvento;
  destino_id: string;
}

export interface EventoResponse {
  id: string;
  titulo: string;
  descricao: string | null;
  data_inicio: string;
  data_fim: string | null;
  local: string | null;
  criado_por: string;
  perfil_criador: string;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

export interface EventoCreate {
  titulo: string;
  descricao?: string | null;
  data_inicio: string;
  data_fim?: string | null;
  local?: string | null;
  destinatarios: EventoDestinatarioCreate[];
}

export interface EventoUpdate {
  titulo?: string;
  descricao?: string | null;
  data_inicio?: string;
  data_fim?: string | null;
  local?: string | null;
  destinatarios?: EventoDestinatarioCreate[];
}

export interface EventoDetalheResponse {
  evento: EventoResponse;
  destinatarios: EventoDestinatarioResponse[];
}

export const agendaApi = {
  list: (params?: { page?: number; size?: number; data_inicio?: string; data_fim?: string }) =>
    paginatedGet<EventoResponse>("/agenda/events", params),
  getById: (id: string) => getById<EventoDetalheResponse>(`/agenda/events/${id}`),
  create: (data: EventoCreate) => create<EventoResponse>("/agenda/events", data),
  update: (id: string, data: EventoUpdate) => update<EventoResponse>(`/agenda/events/${id}`, data),
  delete: (id: string) => api.delete(`/agenda/events/${id}`).then((r) => r.data),
};
