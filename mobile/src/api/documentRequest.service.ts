import { api } from "./client";

export type TipoDocumento =
  | "boletim_bimestral"
  | "boletim_anual"
  | "historico_escolar"
  | "declaracao_matricula"
  | "comprovante_matricula"
  | "comprovante_frequencia"
  | "comprovante_endereco"
  | "comprovante_renda"
  | "outro";

export type StatusSolicitacaoDocumento =
  | "pendente"
  | "em_analise"
  | "concluida"
  | "recusada"
  | "cancelada";

export interface SolicitacaoDocumento {
  id: string;
  aluno_id: string;
  aluno_nome: string | null;
  tipo: TipoDocumento;
  status: StatusSolicitacaoDocumento;
  observacoes: string | null;
  resposta: string | null;
  documento_url: string | null;
  atendido_em: string | null;
  created_at: string;
  updated_at: string;
}

export async function criarSolicitacao(dados: {
  aluno_id: string;
  tipo: TipoDocumento;
  observacoes?: string;
}): Promise<SolicitacaoDocumento> {
  const { data } = await api.post<SolicitacaoDocumento>(
    "/documentos/solicitacoes",
    dados,
  );
  return data;
}

export async function listarSolicitacoes(params?: {
  status?: StatusSolicitacaoDocumento;
}): Promise<SolicitacaoDocumento[]> {
  const { data } = await api.get<SolicitacaoDocumento[]>(
    "/documentos/solicitacoes",
    { params },
  );
  return data;
}

export async function cancelarSolicitacao(
  solicitacaoId: string,
): Promise<SolicitacaoDocumento> {
  const { data } = await api.post<SolicitacaoDocumento>(
    `/documentos/solicitacoes/${solicitacaoId}/cancelar`,
  );
  return data;
}

/** Catálogo exibido na tela, com rótulo e ícone por tipo. */
export const TIPOS_DOCUMENTO: {
  id: TipoDocumento;
  label: string;
  descricao: string;
  icon: string;
}[] = [
  {
    id: "boletim_bimestral",
    label: "Boletim bimestral",
    descricao: "Notas do bimestre atual",
    icon: "document-text-outline",
  },
  {
    id: "boletim_anual",
    label: "Boletim anual",
    descricao: "Notas e médias do ano",
    icon: "school-outline",
  },
  {
    id: "historico_escolar",
    label: "Histórico escolar",
    descricao: "Histórico completo do aluno",
    icon: "time-outline",
  },
  {
    id: "declaracao_matricula",
    label: "Declaração de matrícula",
    descricao: "Comprovante de matrícula",
    icon: "reader-outline",
  },
  {
    id: "comprovante_matricula",
    label: "Comprovante de matrícula",
    descricao: "Documento de matrícula ativo",
    icon: "card-outline",
  },
  {
    id: "comprovante_frequencia",
    label: "Comprovante de frequência",
    descricao: "Relatório de presenças e faltas",
    icon: "calendar-outline",
  },
  {
    id: "comprovante_endereco",
    label: "Comprovante de endereço",
    descricao: "Documento com endereço cadastrado",
    icon: "home-outline",
  },
  {
    id: "comprovante_renda",
    label: "Comprovante de renda",
    descricao: "Para fins de matrícula",
    icon: "cash-outline",
  },
  {
    id: "outro",
    label: "Outro documento",
    descricao: "Descreva o que precisa",
    icon: "ellipsis-horizontal-outline",
  },
];

export const STATUS_SOLICITACAO: Record<
  StatusSolicitacaoDocumento,
  { label: string; cor: string; icon: string }
> = {
  pendente: { label: "Pendente", cor: "#F39C12", icon: "time-outline" },
  em_analise: { label: "Em análise", cor: "#2D7FF9", icon: "hourglass-outline" },
  concluida: { label: "Concluída", cor: "#27AE60", icon: "checkmark-circle-outline" },
  recusada: { label: "Recusada", cor: "#E74C3C", icon: "close-circle-outline" },
  cancelada: { label: "Cancelada", cor: "#7A7A7A", icon: "ban-outline" },
};
