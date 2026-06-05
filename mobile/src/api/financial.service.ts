import { api } from "./client";

export interface SaldoResponse {
  aluno_id: string;
  saldo: number;
}

interface RawSaldoResponse {
  aluno_id: string;
  saldo: string;
}

export interface MovimentacaoItem {
  id: string;
  tipo: "recarga" | "consumo" | "estorno";
  valor: number;
  saldo_anterior: number;
  saldo_posterior: number;
  descricao: string | null;
  criado_por: string | null;
  created_at: string;
}

interface RawMovimentacaoItem {
  id: string;
  tipo: "recarga" | "consumo" | "estorno";
  valor: string;
  saldo_anterior: string;
  saldo_posterior: string;
  descricao: string | null;
  criado_por: string | null;
  created_at: string;
}

export interface ExtratoResponse {
  aluno_id: string;
  movimentacoes: MovimentacaoItem[];
}

interface RawExtratoResponse {
  aluno_id: string;
  movimentacoes: RawMovimentacaoItem[];
}

export interface RecargaRequest {
  valor: number;
}

export interface RecargaResponse {
  movimentacao_id: string;
  saldo_anterior: number;
  valor: number;
  saldo_atual: number;
}

interface RawRecargaResponse {
  movimentacao_id: string;
  saldo_anterior: string;
  valor: string;
  saldo_atual: string;
}

function toNum(v: string): number {
  return parseFloat(v);
}

export async function getBalance(alunoId?: string, signal?: AbortSignal): Promise<SaldoResponse> {
  const { data } = await api.get<RawSaldoResponse>("/financial/me/balance", {
    params: alunoId ? { aluno_id: alunoId } : undefined,
    signal,
  });
  return { aluno_id: data.aluno_id, saldo: toNum(data.saldo) };
}

export async function getStatement(
  params?: { page?: number; size?: number; aluno_id?: string },
  signal?: AbortSignal
): Promise<ExtratoResponse> {
  const { data } = await api.get<RawExtratoResponse>("/financial/me/statement", {
    params: { page: params?.page ?? 1, size: params?.size ?? 20, aluno_id: params?.aluno_id },
    signal,
  });
  return {
    aluno_id: data.aluno_id,
    movimentacoes: data.movimentacoes.map((m) => ({
      ...m,
      valor: toNum(m.valor),
      saldo_anterior: toNum(m.saldo_anterior),
      saldo_posterior: toNum(m.saldo_posterior),
    })),
  };
}

export async function recharge(
  body: RecargaRequest
): Promise<RecargaResponse> {
  const { data } = await api.post<RawRecargaResponse>(
    "/financial/me/recharge",
    body
  );
  return {
    movimentacao_id: data.movimentacao_id,
    saldo_anterior: toNum(data.saldo_anterior),
    valor: toNum(data.valor),
    saldo_atual: toNum(data.saldo_atual),
  };
}
