import { api } from "./client";

// ── Types ────────────────────────────────────────────────────────

export type StatusAviso = "publicado" | "arquivado";

export interface Aviso {
  id: string;
  titulo: string;
  mensagem: string;
  tipo: string;
  prioridade: string;
  destinatario_aluno_id: string | null;
  destinatario_turma_id: string | null;
  permite_respostas: boolean;
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

export type TipoNotificacao =
  | "sistema"
  | "cantina"
  | "boletim"
  | "ocorrencia"
  | "aviso"
  | "agenda"
  | "financeiro"
  | "nota"
  | "frequencia";

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

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ── Avisos ───────────────────────────────────────────────────────

export async function getAvisos(
  params?: { status?: StatusAviso; page?: number; size?: number },
  signal?: AbortSignal,
): Promise<Paginated<Aviso>> {
  const res = await api.get<Paginated<Aviso>>("/avisos", {
    params: { page: params?.page ?? 1, size: params?.size ?? 20, status: params?.status },
    signal,
  });
  return res.data;
}

// ── Notificações ─────────────────────────────────────────────────

export async function getNotificacoes(
  params?: { apenas_nao_lidas?: boolean; page?: number; size?: number },
  signal?: AbortSignal,
): Promise<Paginated<Notificacao>> {
  const res = await api.get<Paginated<Notificacao>>("/notificacoes", {
    params: {
      page: params?.page ?? 1,
      size: params?.size ?? 20,
      apenas_nao_lidas: params?.apenas_nao_lidas,
    },
    signal,
  });
  return res.data;
}

export async function getNotificacoesNaoLidas(
  signal?: AbortSignal,
): Promise<{ total: number }> {
  const res = await api.get<{ total: number }>("/notificacoes/nao-lidas", { signal });
  return res.data;
}

export async function marcarNotificacaoLida(
  id: string,
  signal?: AbortSignal,
): Promise<Notificacao> {
  const res = await api.patch<Notificacao>(`/notificacoes/${id}/ler`, {}, { signal });
  return res.data;
}

export async function marcarTodasNotificacoesLidas(
  signal?: AbortSignal,
): Promise<{ marcadas: number }> {
  const res = await api.patch<{ marcadas: number }>("/notificacoes/ler-todas", {}, { signal });
  return res.data;
}

// ── Preferências de notificação ────────────────────────────────────

export interface PreferenciaNotificacao {
  tipo: TipoNotificacao;
  email: boolean;
  updated_at: string;
}

/** Tipos com canal de e-mail liberado para escolha pelo responsável. */
export const TIPOS_COM_EMAIL: {
  tipo: TipoNotificacao;
  titulo: string;
  descricao: string;
  icone: string;
}[] = [
  {
    tipo: "aviso",
    titulo: "Avisos",
    descricao: "Comunicados e avisos enviados pela escola",
    icone: "megaphone-outline",
  },
  {
    tipo: "ocorrencia",
    titulo: "Ocorrências",
    descricao: "Faltas, atrasos e hechos registrados sobre o aluno",
    icone: "alert-circle-outline",
  },
];

/**
 * Preferências de canal do usuário.
 *
 * O backend devolve todos os tipos de `TipoNotificacao`, então tipos fora de
 * `TIPOS_COM_EMAIL` simplesmente não são oferecidos na tela.
 */
export async function getPreferenciasNotificacao(
  signal?: AbortSignal,
): Promise<Record<string, boolean>> {
  const res = await api.get<{ preferencias: Record<string, boolean> }>(
    "/notificacoes/preferencias",
    { signal },
  );
  return res.data.preferencias;
}

export async function setPreferenciaNotificacaoEmail(
  tipo: TipoNotificacao,
  email: boolean,
): Promise<PreferenciaNotificacao> {
  const res = await api.put<PreferenciaNotificacao>(
    `/notificacoes/preferencias/${tipo}`,
    { email },
  );
  return res.data;
}

// ── Aviso: detalhe, destinatários e conversa ─────────────────────

export interface AvisoDestinatario {
  id: string;
  aviso_id: string;
  usuario_id: string;
  usuario_nome: string | null;
  usuario_perfil: string | null;
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

export async function getAvisoDetalhe(
  avisoId: string,
  signal?: AbortSignal,
): Promise<AvisoDetalhe> {
  const res = await api.get<AvisoDetalhe>(`/avisos/${avisoId}`, { signal });
  return res.data;
}

export async function getAvisoMensagens(
  avisoId: string,
  signal?: AbortSignal,
): Promise<AvisoMensagem[]> {
  const res = await api.get<AvisoMensagem[]>(`/avisos/${avisoId}/mensagens`, { signal });
  return res.data;
}

export async function responderAviso(
  avisoId: string,
  conteudo: string,
  destinatarioId?: string,
  signal?: AbortSignal,
): Promise<AvisoMensagem> {
  const res = await api.post<AvisoMensagem>(
    `/avisos/${avisoId}/respostas`,
    { conteudo, destinatario_id: destinatarioId ?? null },
    { signal },
  );
  return res.data;
}

export async function marcarMensagemLida(
  avisoId: string,
  mensagemId: string,
  signal?: AbortSignal,
): Promise<AvisoMensagem> {
  const res = await api.patch<AvisoMensagem>(
    `/avisos/${avisoId}/mensagens/${mensagemId}/ler`,
    {},
    { signal },
  );
  return res.data;
}

export async function marcarAvisoLido(
  avisoId: string,
  signal?: AbortSignal,
): Promise<void> {
  await api.post(`/avisos/${avisoId}/ler`, {}, { signal });
}

// ── Ocorrências ──────────────────────────────────────────────────

export type StatusOcorrencia = "aberta" | "em_andamento" | "resolvida" | "arquivada";
export type TipoOcorrencia = "comportamento" | "saude" | "academico" | "outro";
export type SeveridadeOcorrencia = "baixa" | "media" | "alta";

export interface OcorrenciaHistorico {
  id: string;
  status_anterior: StatusOcorrencia | null;
  status_novo: StatusOcorrencia | null;
  acao: string;
  autor_id: string | null;
  created_at: string;
}

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

export interface OcorrenciaDetalhe {
  ocorrencia: Ocorrencia;
  historico: OcorrenciaHistorico[];
}

export async function getOcorrencia(
  ocorrenciaId: string,
  signal?: AbortSignal,
): Promise<OcorrenciaDetalhe> {
  const res = await api.get<OcorrenciaDetalhe>(`/ocorrencias/${ocorrenciaId}`, { signal });
  return res.data;
}
