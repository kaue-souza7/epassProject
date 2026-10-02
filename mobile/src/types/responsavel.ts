import type { SituacaoAluno } from ".";

export interface Child {
  aluno_id: string;
  aluno_nome: string;
  matricula_id: string | null;
  turma_codigo: string | null;
  situacao: SituacaoAluno | null;
  media_geral: number | null;
  frequencia_media: number | null;
}

export interface DashboardCards {
  quantidade_filhos: number;
  matriculas_ativas: number;
  media_geral: number | null;
  frequencia_media: number | null;
}

export interface DashboardResponsavel {
  cards: DashboardCards;
  filhos: Child[];
}

export interface MyChildrenResponse {
  id: string;
  nome: string;
  ativo: boolean;
}

export interface SubjectGrade {
  disciplina_id: string;
  disciplina_nome: string;
  nota_maxima: number;
  media: number;
  frequencia: number | null;
  nota_recuperacao: number | null;
  media_pos_recuperacao: number | null;
  situacao: SituacaoAluno | null;
}

export interface ReportCard {
  matricula_id: string;
  aluno_nome: string;
  turma_codigo: string;
  serie_nome: string;
  ano_letivo: number;
  bimestre: number;
  disciplinas: SubjectGrade[];
}

export interface ReportCardAnnual {
  matricula_id: string;
  aluno_nome: string;
  turma_codigo: string;
  serie_nome: string;
  ano_letivo: number;
  bimestres: ReportCard[];
  situacao_final: SituacaoAluno | null;
  media_pre_recuperacao: number | null;
  media_pos_recuperacao: number | null;
}

export interface AgendaEvent {
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

export interface EventDetail {
  evento: AgendaEvent;
  destinatarios: {
    id: string;
    evento_id: string;
    tipo_destino: string;
    destino_id: string;
  }[];
}

export interface FrequencyReport {
  matricula_id: string;
  aluno_nome: string;
  turma_codigo: string;
  ano_letivo: number;
  periodo_inicio: string;
  periodo_fim: string;
  total_aulas: number;
  presencas: number;
  faltas: number;
  faltas_justificadas: number;
  frequencia_media: number;
}

export interface SchoolHistoryDiscipline {
  disciplina_nome: string;
  ano_letivo: number;
  serie_nome: string;
  situacao: string;
  media_final: number | null;
}

export interface SchoolHistory {
  aluno_id: string;
  aluno_nome: string;
  disciplinas: SchoolHistoryDiscipline[];
}

export interface EnrollmentCertificate {
  matricula_id: string;
  aluno_nome: string;
  turma_codigo: string;
  serie_nome: string;
  ano_letivo: number;
  data_emissao: string;
  situacao: string;
}

export interface PaymentReceipt {
  movimento_id: string;
  descricao: string;
  valor: number;
  data_pagamento: string;
  forma_pagamento: string;
  aluno_nome: string;
}

export interface BimestreEvolucao {
  bimestre: number;
  media_geral: number;
  frequencia: number | null;
}

export interface EvolutionData {
  matricula_id: string;
  aluno_nome: string;
  turma_codigo: string;
  serie_nome: string;
  ano_letivo: number;
  bimestres: BimestreEvolucao[];
}

export interface DocumentPdf {
  id: string;
  tipo: string;
  url: string;
  nome_arquivo: string;
}

export type ReportType =
  | "boletim_anual"
  | "boletim_bimestral"
  | "frequencia"
  | "historico_escolar"
  | "declaracao_matricula"
  | "comprovante_pagamento"
  | "extrato_financeiro"
  | "evolucao";

export interface ReportItem {
  id: ReportType;
  title: string;
  description: string;
  icon: string;
  section: "academic" | "financial" | "performance";
}
