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

// ── Grade horária ───────────────────────────────────────────────
// Grade = agenda de aulas (quem tem aula com esta turma, em que dia e horário).
// Não confunda com `Alocacao`, que é a autorização: professor e turma podem ter
// alocação sem ter aula marcada na grade.

export type DiaSemana = "seg" | "ter" | "qua" | "qui" | "sex" | "sab";

export const DIAS_SEMANA_LABEL: Record<DiaSemana, string> = {
  seg: "Segunda",
  ter: "Terça",
  qua: "Quarta",
  qui: "Quinta",
  sex: "Sexta",
  sab: "Sábado",
};

export const DIAS_SEMANA_ORDEM: DiaSemana[] = [
  "seg", "ter", "qua", "qui", "sex", "sab",
];

export interface HorarioAula {
  id: string;
  turma_id: string;
  turma_codigo: string | null;
  turma_turno: string | null;
  professor_id: string;
  professor_nome: string | null;
  disciplina_id: string | null;
  disciplina_nome: string | null;
  dia_semana: DiaSemana;
  hora_inicio: string;
  hora_fim: string;
  ativo: boolean;
}

export interface AulaHoje {
  horario_id: string;
  hora_inicio: string;
  hora_fim: string;
  professor_id: string;
  professor_nome: string | null;
  disciplina_nome: string | null;
  em_curso: boolean;
}

export interface AulasDoDia {
  aluno_id: string;
  aluno_nome: string | null;
  data: string;
  dia_semana: DiaSemana | null;
  sem_aula: boolean;
  motivo_sem_aula: string | null;
  turma_id: string | null;
  turma_codigo: string | null;
  turma_turno: string | null;
  aulas: AulaHoje[];
  professores_ids: string[];
  professores_nomes: string[];
}

export const scheduleApi = {
  list: (params?: {
    turma_id?: string;
    professor_id?: string;
    dia?: DiaSemana[];
    incluir_inativos?: boolean;
  }) => api.get<HorarioAula[]>("/schedule", { params }).then((r) => r.data),
  grid: (turmaId: string, incluirInativos?: boolean) =>
    api
      .get<HorarioAula[]>(`/schedule/grid/${turmaId}`, {
        params: incluirInativos ? { incluir_inativos: true } : undefined,
      })
      .then((r) => r.data),
  getById: (id: string) => getById<HorarioAula>(`/schedule/${id}`),
  create: (data: {
    turma_id: string;
    professor_id: string;
    disciplina_id?: string | null;
    dia_semana: DiaSemana;
    hora_inicio: string;
    hora_fim: string;
  }) => create<HorarioAula>("/schedule", data),
  update: (id: string, data: Partial<{
    professor_id: string;
    disciplina_id: string | null;
    dia_semana: DiaSemana;
    hora_inicio: string;
    hora_fim: string;
    ativo: boolean;
  }>) => update<HorarioAula>(`/schedule/${id}`, data),
  desativar: (id: string) =>
    api.patch<HorarioAula>(`/schedule/${id}/desativar`).then((r) => r.data),
  reativar: (id: string) =>
    api.patch<HorarioAula>(`/schedule/${id}/reativar`).then((r) => r.data),
  aulasDoDia: (alunoId: string, data?: string) =>
    api
      .get<AulasDoDia>("/schedule/aulas-do-dia", {
        params: { aluno_id: alunoId, ...(data ? { data } : {}) },
      })
      .then((r) => r.data),
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
  situacao_final: string | null;
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

export interface PrazoLiberacaoResponse {
  id: string;
  ano_letivo_id: string;
  bimestre: number;
  data_limite: string;
  hora_limite: string;
  notificado_em: string | null;
  ativo: boolean;
}

export interface PrazoLiberacaoCreate {
  ano_letivo_id: string;
  bimestre: number;
  data_limite: string;
  hora_limite: string;
}

export const boletimLiberacaoApi = {
  liberar: (turmaId: string, bimestre: number) =>
    api.post<LiberacaoBoletimResponse[]>("/boletim-liberacao", { turma_id: turmaId, bimestre }).then((r) => r.data),
  getStatus: (turmaId: string, bimestre: number) =>
    api.get<LiberacaoStatusResponse>("/boletim-liberacao/status", { params: { turma_id: turmaId, bimestre } }).then((r) => r.data),
  listarPrazos: (anoLetivoId: string) =>
    api.get<PrazoLiberacaoResponse[]>("/boletim-liberacao/prazos", { params: { ano_letivo_id: anoLetivoId } }).then((r) => r.data),
  criarPrazo: (data: PrazoLiberacaoCreate) =>
    api.post<PrazoLiberacaoResponse>("/boletim-liberacao/prazos", data).then((r) => r.data),
  atualizarPrazo: (prazoId: string, data: { data_limite?: string; hora_limite?: string; ativo?: boolean }) =>
    api.put<PrazoLiberacaoResponse>(`/boletim-liberacao/prazos/${prazoId}`, data).then((r) => r.data),
};

// System Config - SMTP
export interface SmtpConfigResponse {
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_user: string | null;
  smtp_from: string | null;
  smtp_use_tls: boolean | null;
  smtp_use_ssl: boolean | null;
  configured: boolean;
}

export interface SmtpConfigRequest {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password?: string;
  smtp_from: string;
  smtp_use_tls: boolean;
  smtp_use_ssl: boolean;
}

export interface SmtpTestResponse {
  success: boolean;
  message: string;
}

// Cantina - Products
export type CategoriaProduto = "SALGADO" | "LANCHE_QUENTE" | "LANCHE_NATURAL" | "DOCE" | "BOMBONIERE";

export const CATEGORIA_PRODUTO_LABELS: Record<CategoriaProduto, string> = {
  SALGADO: "Salgados",
  LANCHE_QUENTE: "Lanches Quentes",
  LANCHE_NATURAL: "Lanches Naturais",
  DOCE: "Doces",
  BOMBONIERE: "Bomboniere",
};

export interface Produto {
  id: string;
  nome: string;
  descricao: string | null;
  preco: number;
  custo: number | null;
  imagem_url: string | null;
  categoria: CategoriaProduto;
  estoque_atual: number;
  estoque_minimo: number;
  codigo: string | null;
  unidade_medida: string | null;
  perecivel: boolean;
  data_validade: string | null;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProdutoCreateRequest {
  nome: string;
  descricao?: string;
  preco: number;
  custo?: number;
  imagem_url?: string;
  categoria: CategoriaProduto;
  estoque_atual?: number;
  estoque_minimo?: number;
  codigo?: string;
  unidade_medida?: string;
  perecivel?: boolean;
  data_validade?: string;
}

export interface ProdutoUpdateRequest {
  nome?: string;
  descricao?: string;
  preco?: number;
  custo?: number;
  imagem_url?: string;
  categoria?: CategoriaProduto;
  estoque_minimo?: number;
  codigo?: string;
  unidade_medida?: string;
  perecivel?: boolean;
  data_validade?: string;
}

export interface EstoqueResponse {
  produto_id: string;
  estoque_anterior: number;
  quantidade: number;
  estoque_atual: number;
  motivo: string | null;
}

// Cantina - Orders
export type StatusPedido = "pendente" | "aprovado" | "em_producao" | "pronto" | "retirado" | "cancelado";

export interface ItemPedido {
  id: string;
  produto_id: string;
  produto_nome: string | null;
  quantidade: number;
  preco_unitario: number;
  preco_total: number;
}

export interface Pedido {
  id: string;
  aluno_id: string;
  aluno_nome: string | null;
  responsavel_id: string;
  status: StatusPedido;
  valor_total: number;
  saldo_debitado: number;
  movimentacao_id: string | null;
  observacoes: string | null;
  itens: ItemPedido[];
  created_at: string;
  updated_at: string;
}

export interface PedidoListItem {
  id: string;
  aluno_id: string;
  aluno_nome: string | null;
  aluno_turma: string | null;
  status: StatusPedido;
  valor_total: number;
  observacoes: string | null;
  itens: ItemPedido[];
  created_at: string;
}

export interface PedidoStatusResponse {
  id: string;
  status: StatusPedido;
  mensagem: string;
}

// O backend serializa Decimal como string; normalizamos para number no front.
function toNum(v: unknown): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") return parseFloat(v) || 0;
  return 0;
}

function normalizeProduto(p: any): Produto {
  return {
    ...p,
    preco: toNum(p.preco),
    custo: p.custo == null ? null : toNum(p.custo),
  };
}

function normalizeItemPedido(i: any): ItemPedido {
  return {
    ...i,
    preco_unitario: toNum(i.preco_unitario),
    preco_total: toNum(i.preco_total),
  };
}

function normalizePedido(p: any): Pedido {
  return {
    ...p,
    valor_total: toNum(p.valor_total),
    saldo_debitado: toNum(p.saldo_debitado),
    itens: (p.itens || []).map(normalizeItemPedido),
  };
}

function normalizePedidoListItem(p: any): PedidoListItem {
  return {
    ...p,
    valor_total: toNum(p.valor_total),
    itens: (p.itens || []).map(normalizeItemPedido),
  };
}

export const cantinaProductsApi = {
  list: (params?: { ativo?: boolean; page?: number; size?: number }) =>
    paginatedGet<Produto>("/cantina/products", params).then((r) => ({
      ...r,
      items: r.items.map(normalizeProduto),
    })),
  getById: (id: string) =>
    getById<Produto>(`/cantina/products/${id}`).then(normalizeProduto),
  create: (data: ProdutoCreateRequest) =>
    create<Produto>("/cantina/products", data).then(normalizeProduto),
  update: (id: string, data: ProdutoUpdateRequest) =>
    update<Produto>(`/cantina/products/${id}`, data).then(normalizeProduto),
  toggle: (id: string) =>
    api.patch<Produto>(`/cantina/products/${id}/toggle`).then((r) => normalizeProduto(r.data)),
  adjustStock: (id: string, data: { quantidade: number; motivo?: string }) =>
    api.post<EstoqueResponse>(`/cantina/products/${id}/stock`, data).then((r) => r.data),
};

// Cantina - Student Search
export interface CantinaStudent {
  id: string;
  nome: string;
  turma: string | null;
  saldo: number;
  autonomia_cantina: boolean;
}

export const cantinaStudentsApi = {
  search: (q: string) =>
    api
      .get<CantinaStudent[]>("/cantina/students/search", { params: { q } })
      .then((r) => r.data.map((s) => ({ ...s, saldo: toNum(s.saldo) }))),
};

// Cantina - Autonomy
export interface AutonomiaResponse {
  aluno_id: string;
  autonomia_cantina: boolean;
}

export const cantinaAutonomiaApi = {
  get: (alunoId: string) =>
    api.get<AutonomiaResponse>(`/cantina/students/${alunoId}/autonomy`).then((r) => r.data),
  set: (alunoId: string, autonomia: boolean) =>
    api.put<AutonomiaResponse>(`/cantina/students/${alunoId}/autonomy`, {
      autonomia_cantina: autonomia,
    }).then((r) => r.data),
};

// Cantina - Direct Consumption
export interface ConsumoDiretoItem {
  produto_id: string;
  quantidade: number;
}

export interface ConsumoDiretoRequest {
  aluno_id: string;
  itens: ConsumoDiretoItem[];
  idempotency_key?: string;
}

export interface ConsumoDiretoResponse {
  consumo_id: string;
  aluno_id: string;
  aluno_nome: string | null;
  valor_total: number;
  saldo_anterior: number;
  saldo_atual: number;
  movimentacao_id: string;
  itens: ItemPedido[];
  created_at: string;
}

export const cantinaConsumoApi = {
  create: (data: ConsumoDiretoRequest) =>
    api.post<ConsumoDiretoResponse>("/cantina/consumo-direto", data).then((r) => ({
      ...r.data,
      valor_total: toNum(r.data.valor_total),
      saldo_anterior: toNum(r.data.saldo_anterior),
      saldo_atual: toNum(r.data.saldo_atual),
      itens: (r.data.itens || []).map(normalizeItemPedido),
    })),
};

export const cantinaOrdersApi = {
  list: (params?: { status?: string; page?: number; size?: number }) =>
    paginatedGet<PedidoListItem>("/cantina/orders", params).then((r) => ({
      ...r,
      items: r.items.map(normalizePedidoListItem),
    })),
  getById: (id: string) =>
    getById<Pedido>(`/cantina/orders/${id}`).then(normalizePedido),
  approve: (id: string) =>
    api.patch<Pedido>(`/cantina/orders/${id}/approve`).then((r) => normalizePedido(r.data)),
  reject: (id: string) =>
    api.patch<Pedido>(`/cantina/orders/${id}/reject`).then((r) => normalizePedido(r.data)),
  produce: (id: string) =>
    api.patch<Pedido>(`/cantina/orders/${id}/produce`).then((r) => normalizePedido(r.data)),
  ready: (id: string) =>
    api.patch<Pedido>(`/cantina/orders/${id}/ready`).then((r) => normalizePedido(r.data)),
  delivered: (id: string) =>
    api.patch<Pedido>(`/cantina/orders/${id}/delivered`).then((r) => normalizePedido(r.data)),
  cancel: (id: string) =>
    api.patch<Pedido>(`/cantina/orders/${id}/cancel`).then((r) => normalizePedido(r.data)),
  history: (id: string) =>
    api.get<any[]>(`/cantina/orders/${id}/history`).then((r) => r.data),
};

// Cantina - Stock History
export interface MovimentacaoEstoque {
  id: string;
  produto_id: string;
  tipo: "entrada" | "saida" | "ajuste";
  quantidade: number;
  estoque_anterior: number;
  estoque_atual: number;
  motivo: string | null;
  usuario_nome: string | null;
  created_at: string;
}

export const cantinaStockHistoryApi = {
  list: (produtoId: string, params?: { page?: number; size?: number }) =>
    paginatedGet<MovimentacaoEstoque>(`/cantina/products/${produtoId}/stock-history`, params),
};

export const cantinaDashboardApi = {
  get: () => api.get("/cantina/dashboard").then((r) => r.data),
};

export const cantinaUploadApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<{ url: string }>("/cantina/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data);
  },
};

// Cantina - Config
export interface CantinaConfig {
  id: string;
  aberta: boolean;
  horario_abertura: string | null;
  horario_fechamento: string | null;
  dias_funcionamento: string | null;
  prazo_pedido_minutos: number | null;
  prazo_cancelamento_minutos: number | null;
  timezone: string | null;
  observacoes: string | null;
}

export interface CantinaConfigUpdateRequest {
  aberta?: boolean;
  horario_abertura?: string;
  horario_fechamento?: string;
  dias_funcionamento?: string;
  prazo_pedido_minutos?: number;
  prazo_cancelamento_minutos?: number;
  timezone?: string;
  observacoes?: string;
}

export const cantinaConfigApi = {
  get: () =>
    api.get<CantinaConfig>("/cantina/config").then((r) => r.data),
  update: (data: CantinaConfigUpdateRequest) =>
    api.put<CantinaConfig>("/cantina/config", data).then((r) => r.data),
};

// Financial - Carteiras (admin)
export interface WalletDetail {
  id: string;
  aluno_id: string;
  saldo: string | number;
  status: "ativa" | "bloqueada" | "cancelada";
  created_at: string;
  updated_at: string;
  aluno_nome: string | null;
}

export const financialApi = {
  listWallets: (params?: { status?: string; page?: number; size?: number }) =>
    paginatedGet<WalletDetail>("/financial/wallets", params),
  getWallet: (walletId: string) =>
    getById<WalletDetail>(`/financial/wallets/${walletId}`),
  blockWallet: (walletId: string) =>
    api.patch<WalletDetail>(`/financial/wallets/${walletId}/block`).then((r) => r.data),
  unblockWallet: (walletId: string) =>
    api.patch<WalletDetail>(`/financial/wallets/${walletId}/unblock`).then((r) => r.data),
};

// ── Comunicação: Avisos, Ocorrências e Notificações ───────────────

export type StatusAviso = "publicado" | "arquivado";
export type StatusOcorrencia = "aberta" | "em_andamento" | "resolvida" | "arquivada";
export type TipoOcorrencia = "comportamento" | "saude" | "academico" | "outro";
export type SeveridadeOcorrencia = "baixa" | "media" | "alta";
export type TipoNotificacao =
  | "sistema" | "cantina" | "boletim" | "ocorrencia" | "aviso"
  | "agenda" | "financeiro" | "nota" | "frequencia";

export type CaixaAviso = "recebidos" | "enviados" | "todos" | "global";

export interface Aviso {
  id: string;
  titulo: string;
  mensagem: string;
  tipo: string;
  prioridade: string;
  permite_respostas: boolean;
  destinatario_aluno_id: string | null;
  destinatario_turma_id: string | null;
  status: StatusAviso;
  criado_por: string;
  autor_nome: string | null;
  autor_perfil: string | null;
  publicado_em: string;
  created_at: string;
  lido_por_mim: boolean;
  sou_autor: boolean;
  total_destinatarios: number;
  lidos: number;
  nao_lidos: number;
}

export interface AvisoDestinatario {
  id: string;
  aviso_id: string;
  usuario_id: string;
  usuario_nome: string | null;
  usuario_perfil: string | null;
  aluno_id: string | null;
  aluno_nome: string | null;
  lido_em: string | null;
  escalado_em: string | null;
  created_at: string;
}

export interface AvisoEstatisticas {
  total: number;
  lidos: number;
  nao_lidos: number;
}

export interface AvisoMensagem {
  id: string;
  aviso_id: string;
  autor_id: string;
  autor_nome: string | null;
  autor_perfil: string | null;
  destinatario_id: string;
  destinatario_nome: string | null;
  conteudo: string;
  lida_em: string | null;
  created_at: string;
  enviada_por_mim: boolean;
}

export interface AvisoDetalhe {
  aviso: Aviso;
  destinatarios: AvisoDestinatario[];
  estatisticas: AvisoEstatisticas;
  pode_responder: boolean;
  total_mensagens: number;
}

export interface PublicoPessoa {
  id: string;
  nome: string;
  aluno_id?: string | null;
  aluno_nome?: string | null;
  turma_codigo?: string | null;
}

export interface PublicoTurma {
  id: string;
  codigo: string;
  nome?: string | null;
}

export interface PublicoDisponivel {
  professores: PublicoPessoa[];
  responsaveis: PublicoPessoa[];
  turmas: PublicoTurma[];
  pode_enviar_para_professores: boolean;
  pode_enviar_para_todos_responsaveis: boolean;
}

export interface AvisoCreateRequest {
  titulo: string;
  mensagem: string;
  tipo?: string;
  prioridade?: string;
  permite_respostas?: boolean;
  para_professores?: boolean;
  professor_ids?: string[];
  para_responsaveis?: boolean;
  responsavel_ids?: string[];
  turma_ids?: string[];
}

export const avisosApi = {
  list: (params?: {
    caixa?: CaixaAviso;
    status?: StatusAviso;
    busca?: string;
    page?: number;
    size?: number;
  }) => paginatedGet<Aviso>("/avisos", params),
  getById: (id: string) => getById<AvisoDetalhe>(`/avisos/${id}`),
  create: (data: AvisoCreateRequest) => create<Aviso>("/avisos", data),
  update: (id: string, data: Partial<AvisoCreateRequest>) =>
    update<Aviso>(`/avisos/${id}`, data),
  arquivar: (id: string) =>
    api.patch<Aviso>(`/avisos/${id}/arquivar`).then((r) => r.data),
  marcarLido: (id: string) =>
    api.post<AvisoDestinatario>(`/avisos/${id}/ler`).then((r) => r.data),
  publico: () => getById<PublicoDisponivel>("/avisos/publico"),
  destinatarios: (id: string) =>
    getById<AvisoDestinatario[]>(`/avisos/${id}/destinatarios`),
  mensagens: (id: string) =>
    getById<AvisoMensagem[]>(`/avisos/${id}/mensagens`),
  responder: (id: string, conteudo: string, destinatarioId?: string) =>
    api
      .post<AvisoMensagem>(`/avisos/${id}/respostas`, {
        conteudo,
        destinatario_id: destinatarioId ?? null,
      })
      .then((r) => r.data),
  marcarMensagemLida: (avisoId: string, mensagemId: string) =>
    api
      .patch<AvisoMensagem>(`/avisos/${avisoId}/mensagens/${mensagemId}/ler`)
      .then((r) => r.data),
};

export interface Ocorrencia {
  id: string;
  aluno_id: string | null;
  aluno_nome: string | null;
  turma_id: string | null;
  turma_codigo: string | null;
  titulo: string;
  descricao: string;
  tipo: TipoOcorrencia;
  severidade: SeveridadeOcorrencia;
  status: StatusOcorrencia;
  criado_por: string;
  responsavel_id: string | null;
  resolvida_em: string | null;
  created_at: string;
  updated_at: string;
}

export interface OcorrenciaHistorico {
  id: string;
  status_anterior: StatusOcorrencia | null;
  status_novo: StatusOcorrencia | null;
  acao: string;
  autor_id: string | null;
  created_at: string;
}

export interface OcorrenciaDetalhe {
  ocorrencia: Ocorrencia;
  historico: OcorrenciaHistorico[];
}

export interface OcorrenciaCreateRequest {
  aluno_id?: string | null;
  turma_id?: string | null;
  titulo: string;
  descricao: string;
  tipo?: TipoOcorrencia;
  severidade?: SeveridadeOcorrencia;
  responsavel_id?: string | null;
}

export const ocorrenciasApi = {
  list: (params?: {
    status?: StatusOcorrencia;
    aluno_id?: string;
    page?: number;
    size?: number;
  }) => paginatedGet<Ocorrencia>("/ocorrencias", params),
  getById: (id: string) => getById<OcorrenciaDetalhe>(`/ocorrencias/${id}`),
  create: (data: OcorrenciaCreateRequest) => create<Ocorrencia>("/ocorrencias", data),
  update: (id: string, data: Partial<OcorrenciaCreateRequest>) =>
    update<Ocorrencia>(`/ocorrencias/${id}`, data),
  mudarStatus: (id: string, status: StatusOcorrencia, observacao?: string) =>
    api
      .patch<Ocorrencia>(`/ocorrencias/${id}/status`, { status, observacao })
      .then((r) => r.data),
};

export interface Notificacao {
  id: string;
  destinatario_id: string;
  tipo: TipoNotificacao;
  titulo: string;
  mensagem: string;
  canal: string;
  entidade_tipo: string | null;
  entidade_id: string | null;
  dados: Record<string, unknown> | null;
  lida: boolean;
  lida_em: string | null;
  created_at: string;
}

export const notificacoesApi = {
  list: (params?: { apenas_nao_lidas?: boolean; page?: number; size?: number }) =>
    paginatedGet<Notificacao>("/notificacoes", params),
  naoLidas: () =>
    api.get<{ total: number }>("/notificacoes/nao-lidas").then((r) => r.data),
  marcarLida: (id: string) =>
    api.patch<Notificacao>(`/notificacoes/${id}/ler`).then((r) => r.data),
  marcarTodasLidas: () =>
    api.patch<{ marcadas: number }>("/notificacoes/ler-todas").then((r) => r.data),
};

export interface AvisoConfigResponse {
  escalonamento_horas: number;
}

export const systemConfigApi = {
  getSmtp: () => api.get<SmtpConfigResponse>("/system-config/smtp").then((r) => r.data),
  saveSmtp: (data: SmtpConfigRequest) => api.put<SmtpConfigResponse>("/system-config/smtp", data).then((r) => r.data),
  testSmtp: (destinatario: string) =>
    api.post<SmtpTestResponse>("/system-config/smtp/test", { destinatario }).then((r) => r.data),
  getAvisoConfig: () =>
    api.get<AvisoConfigResponse>("/system-config/avisos").then((r) => r.data),
  saveAvisoConfig: (escalonamento_horas: number) =>
    api
      .put<AvisoConfigResponse>("/system-config/avisos", { escalonamento_horas })
      .then((r) => r.data),
};
