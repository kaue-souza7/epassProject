import { useState, useCallback, useEffect, useRef } from "react";
import {
  getBalance,
  getStatement,
  recharge as apiRecharge,
  type ExtratoResponse,
  type MovimentacaoItem,
  type RecargaResponse,
} from "../api/financial.service";
import { getApiErrorMessage } from "../api/errors";
import { useSelectedStudent } from "./useSelectedStudent";
import { useApi } from "./useApi";

const PAGE_SIZE = 20;

interface WalletData {
  saldo: number;
  ultimaMovimentacao: string;
}

interface UseWalletResult {
  saldo: number | null;
  ultimaMovimentacao: string | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

function isCredito(tipo: MovimentacaoItem["tipo"]): boolean {
  return tipo === "recarga" || tipo === "estorno";
}

export function useWallet(): UseWalletResult {
  const { selectedChild } = useSelectedStudent();
  const alunoId = selectedChild?.aluno_id;

  const fetchWallet = useCallback(
    async (signal: AbortSignal): Promise<WalletData> => {
      const balance = await getBalance(alunoId, signal);
      const statement = await getStatement({ size: 1, aluno_id: alunoId }, signal);
      const ultimaMov =
        statement.movimentacoes.length > 0
          ? `${isCredito(statement.movimentacoes[0].tipo) ? "+" : "-"} R$ ${statement.movimentacoes[0].valor.toFixed(2)} - ${statement.movimentacoes[0].descricao ?? ""}`
          : "Nenhuma movimentação";
      return { saldo: balance.saldo, ultimaMovimentacao: ultimaMov };
    },
    [alunoId]
  );

  const { data, loading, error, refetch } = useApi(
    fetchWallet,
    [alunoId],
    { enabled: !!alunoId, errorMessage: "Erro ao carregar carteira" }
  );

  return {
    saldo: data?.saldo ?? null,
    ultimaMovimentacao: data?.ultimaMovimentacao ?? null,
    loading,
    error,
    refetch,
  };
}

interface UseRechargeResult {
  realizarRecarga: (valor: number, idempotencyKey?: string) => Promise<RecargaResponse>;
  loading: boolean;
  error: string | null;
}

export function useRecharge(): UseRechargeResult {
  const { selectedChild } = useSelectedStudent();
  const alunoId = selectedChild?.aluno_id;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const realizarRecarga = useCallback(
    async (valor: number, idempotencyKey?: string): Promise<RecargaResponse> => {
      setLoading(true);
      setError(null);
      try {
        const result = await apiRecharge({ valor, idempotency_key: idempotencyKey }, alunoId);
        return result;
      } catch (err: unknown) {
        const message = getApiErrorMessage(err, "Erro ao realizar recarga");
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [alunoId]
  );

  return { realizarRecarga, loading, error };
}

interface UseStatementResult {
  extrato: ExtratoResponse | null;
  movimentacoes: MovimentacaoItem[];
  loading: boolean;
  loadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  refetch: () => Promise<void>;
  loadMore: () => Promise<void>;
}

export function useStatement(size: number = PAGE_SIZE): UseStatementResult {
  const { selectedChild } = useSelectedStudent();
  const alunoId = selectedChild?.aluno_id;

  const [extrato, setExtrato] = useState<ExtratoResponse | null>(null);
  const [movimentacoes, setMovimentacoes] = useState<MovimentacaoItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pageRef = useRef(1);

  const loadFirstPage = useCallback(async () => {
    if (!alunoId) {
      setMovimentacoes([]);
      setExtrato(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getStatement({ page: 1, size, aluno_id: alunoId });
      pageRef.current = 1;
      setExtrato(result);
      setMovimentacoes(result.movimentacoes);
    } catch (err) {
      setError(getApiErrorMessage(err, "Erro ao carregar extrato"));
    } finally {
      setLoading(false);
    }
  }, [alunoId, size]);

  const loadMore = useCallback(async () => {
    if (!alunoId || loadingMore) return;
    const pages = extrato?.pages ?? 0;
    const nextPage = pageRef.current + 1;
    if (pages > 0 && nextPage > pages) return;

    setLoadingMore(true);
    try {
      const result = await getStatement({ page: nextPage, size, aluno_id: alunoId });
      pageRef.current = nextPage;
      setExtrato(result);
      setMovimentacoes((prev) => {
        const vistos = new Set(prev.map((m) => m.id));
        return [...prev, ...result.movimentacoes.filter((m) => !vistos.has(m.id))];
      });
    } catch (err) {
      setError(getApiErrorMessage(err, "Erro ao carregar mais movimentações"));
    } finally {
      setLoadingMore(false);
    }
  }, [alunoId, size, extrato, loadingMore]);

  const refetch = useCallback(async () => {
    await loadFirstPage();
  }, [loadFirstPage]);

  // Carga inicial / troca de aluno.
  useEffect(() => {
    void loadFirstPage();
  }, [loadFirstPage]);

  const total = extrato?.total ?? movimentacoes.length;
  const pages = extrato?.pages ?? 0;
  const hasMore = pages > 0 ? pageRef.current < pages : false;

  return {
    extrato: extrato ? { ...extrato, total } : null,
    movimentacoes,
    loading,
    loadingMore,
    error,
    hasMore,
    refetch,
    loadMore,
  };
}
