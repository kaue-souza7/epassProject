import { api } from "./client";

// ── Types ────────────────────────────────────────────────────────

export interface MenuItem {
  id: string;
  nome: string;
  descricao: string | null;
  preco: number;
  imagem_url: string | null;
  disponivel: boolean;
}

export interface MenuResponse {
  itens: MenuItem[];
}

export interface ItemPedidoCreate {
  produto_id: string;
  quantidade: number;
}

export interface PedidoCreate {
  aluno_id: string;
  itens: ItemPedidoCreate[];
  observacoes?: string;
}

export interface ItemPedido {
  id: string;
  produto_id: string;
  produto_nome: string | null;
  quantidade: number;
  preco_unitario: number;
  preco_total: number;
}

export type StatusPedido =
  | "pendente"
  | "aprovado"
  | "em_producao"
  | "pronto"
  | "retirado"
  | "cancelado";

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
  status: StatusPedido;
  valor_total: number;
  created_at: string;
}

// ── Helpers ──────────────────────────────────────────────────────

function toNum(v: unknown): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") return parseFloat(v) || 0;
  return 0;
}

// ── API Functions ────────────────────────────────────────────────

export async function getMenu(
  signal?: AbortSignal,
): Promise<MenuItem[]> {
  const res = await api.get<MenuResponse>("/cantina/menu", { signal });
  return (res.data.itens || []).map((item: MenuItem) => ({
    ...item,
    preco: toNum(item.preco),
  }));
}

export async function createOrder(
  data: PedidoCreate,
  signal?: AbortSignal,
): Promise<Pedido> {
  const res = await api.post<Pedido>("/cantina/orders", data, { signal });
  const d = res.data;
  return {
    ...d,
    valor_total: toNum(d.valor_total),
    saldo_debitado: toNum(d.saldo_debitado),
    itens: (d.itens || []).map((item: ItemPedido) => ({
      ...item,
      preco_unitario: toNum(item.preco_unitario),
      preco_total: toNum(item.preco_total),
    })),
  };
}

export async function getTodayOrder(
  alunoId: string,
  signal?: AbortSignal,
): Promise<Pedido | null> {
  const res = await api.get<Pedido | null>("/cantina/me/orders/today", {
    params: { aluno_id: alunoId },
    signal,
  });
  if (!res.data) return null;
  const d = res.data;
  return {
    ...d,
    valor_total: toNum(d.valor_total),
    saldo_debitado: toNum(d.saldo_debitado),
    itens: (d.itens || []).map((item: ItemPedido) => ({
      ...item,
      preco_unitario: toNum(item.preco_unitario),
      preco_total: toNum(item.preco_total),
    })),
  };
}

export async function getOrder(
  orderId: string,
  signal?: AbortSignal,
): Promise<Pedido> {
  const res = await api.get<Pedido>(`/cantina/me/orders/${orderId}`, {
    signal,
  });
  const d = res.data;
  return {
    ...d,
    valor_total: toNum(d.valor_total),
    saldo_debitado: toNum(d.saldo_debitado),
    itens: (d.itens || []).map((item: ItemPedido) => ({
      ...item,
      preco_unitario: toNum(item.preco_unitario),
      preco_total: toNum(item.preco_total),
    })),
  };
}

export async function getMyOrders(
  params: { page?: number; size?: number; aluno_id?: string },
  signal?: AbortSignal,
): Promise<{ items: PedidoListItem[]; total: number }> {
  const res = await api.get("/cantina/me/orders", {
    params,
    signal,
  });
  const data = res.data as { items: PedidoListItem[]; total: number };
  return {
    items: (data.items || []).map((item: PedidoListItem) => ({
      ...item,
      valor_total: toNum(item.valor_total),
    })),
    total: data.total,
  };
}

// ── Programacao Types ────────────────────────────────────────────

export type DiaSemana = "seg" | "ter" | "qua" | "qui" | "sex" | "sab";
export type TipoProgramacao = "diaria" | "geral";

export interface ProgramacaoItem {
  id: string;
  produto_id: string;
  produto_nome: string | null;
  quantidade: number;
}

export interface Programacao {
  id: string;
  aluno_id: string;
  responsavel_id: string;
  dia_semana: DiaSemana;
  tipo: TipoProgramacao;
  ativo: boolean;
  observacoes: string | null;
  itens: ProgramacaoItem[];
  created_at: string;
  updated_at: string;
}

export interface ProgramacaoSemana {
  aluno_id: string;
  programacoes: Programacao[];
}

export interface ProgramacaoItemCreate {
  produto_id: string;
  quantidade: number;
}

export interface ProgramacaoCreate {
  aluno_id: string;
  dia_semana: DiaSemana;
  tipo: TipoProgramacao;
  itens: ProgramacaoItemCreate[];
  observacoes?: string;
}

// ── Programacao API Functions ────────────────────────────────────

export async function getProgramacaoSemana(
  alunoId: string,
  signal?: AbortSignal,
): Promise<ProgramacaoSemana> {
  const res = await api.get<ProgramacaoSemana>(
    `/cantina/programacao/${alunoId}`,
    { signal },
  );
  return res.data;
}

export async function saveProgramacao(
  data: ProgramacaoCreate,
  signal?: AbortSignal,
): Promise<Programacao> {
  const res = await api.post<Programacao>("/cantina/programacao", data, {
    signal,
  });
  return res.data;
}

export async function deleteProgramacao(
  programacaoId: string,
  signal?: AbortSignal,
): Promise<void> {
  await api.delete(`/cantina/programacao/${programacaoId}`, { signal });
}

// ── Autonomia ──────────────────────────────────────────────────

export interface AutonomiaResponse {
  aluno_id: string;
  autonomia_cantina: boolean;
}

export async function getAutonomia(
  alunoId: string,
  signal?: AbortSignal,
): Promise<AutonomiaResponse> {
  const res = await api.get<AutonomiaResponse>(
    `/cantina/students/${alunoId}/autonomy`,
    { signal },
  );
  return res.data;
}

export async function setAutonomia(
  alunoId: string,
  autonomia: boolean,
  signal?: AbortSignal,
): Promise<AutonomiaResponse> {
  const res = await api.put<AutonomiaResponse>(
    `/cantina/students/${alunoId}/autonomy`,
    { autonomia_cantina: autonomia },
    { signal },
  );
  return res.data;
}

// ── Cancel Order ──────────────────────────────────────────────

export async function cancelOrder(
  orderId: string,
  signal?: AbortSignal,
): Promise<Pedido> {
  const res = await api.patch<Pedido>(
    `/cantina/me/orders/${orderId}/cancel`,
    {},
    { signal },
  );
  const d = res.data;
  return {
    ...d,
    valor_total: toNum(d.valor_total),
    saldo_debitado: toNum(d.saldo_debitado),
    itens: (d.itens || []).map((item: ItemPedido) => ({
      ...item,
      preco_unitario: toNum(item.preco_unitario),
      preco_total: toNum(item.preco_total),
    })),
  };
}
