import { useState, useCallback } from "react";
import {
  getBalance,
  getStatement,
  recharge as apiRecharge,
  type ExtratoResponse,
  type RecargaResponse,
  type RecargaRequest,
} from "../api/financial.service";
import { useSelectedStudent } from "./useSelectedStudent";
import { useApi } from "./useApi";

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

export function useWallet(): UseWalletResult {
  const { selectedChild } = useSelectedStudent();
  const alunoId = selectedChild?.aluno_id;

  const fetchWallet = useCallback(
    async (signal: AbortSignal): Promise<WalletData> => {
      const balance = await getBalance(alunoId, signal);
      const statement = await getStatement({ size: 1, aluno_id: alunoId }, signal);
      const ultimaMov =
        statement.movimentacoes.length > 0
          ? `${statement.movimentacoes[0].tipo === "recarga" ? "+" : "-"} R$ ${statement.movimentacoes[0].valor.toFixed(2)} - ${statement.movimentacoes[0].descricao ?? ""}`
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
  realizarRecarga: (valor: number) => Promise<RecargaResponse>;
  loading: boolean;
  error: string | null;
}

export function useRecharge(): UseRechargeResult {
  const { selectedChild } = useSelectedStudent();
  const alunoId = selectedChild?.aluno_id;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const realizarRecarga = useCallback(
    async (valor: number): Promise<RecargaResponse> => {
      setLoading(true);
      setError(null);
      try {
        const result = await apiRecharge({ valor });
        return result;
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Erro ao realizar recarga";
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
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useStatement(
  page: number = 1,
  size: number = 20
): UseStatementResult {
  const { selectedChild } = useSelectedStudent();
  const alunoId = selectedChild?.aluno_id;

  const { data: extrato, loading, error, refetch } = useApi(
    (signal) => getStatement({ page, size, aluno_id: alunoId }, signal),
    [page, size, alunoId],
    { enabled: !!alunoId, errorMessage: "Erro ao carregar extrato" }
  );

  return { extrato, loading, error, refetch };
}
