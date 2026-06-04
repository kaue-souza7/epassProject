import { useState, useEffect, useCallback } from "react";
import {
  getBalance,
  getStatement,
  recharge as apiRecharge,
  type SaldoResponse,
  type ExtratoResponse,
  type RecargaResponse,
  type RecargaRequest,
} from "../api/financial.service";

interface UseWalletResult {
  saldo: number | null;
  ultimaMovimentacao: string | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useWallet(): UseWalletResult {
  const [saldo, setSaldo] = useState<number | null>(null);
  const [ultimaMovimentacao, setUltimaMovimentacao] = useState<string | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const balance = await getBalance();
      const statement = await getStatement({ size: 1 });
      setSaldo(balance.saldo);
      if (statement.movimentacoes.length > 0) {
        const last = statement.movimentacoes[0];
        setUltimaMovimentacao(
          `${last.tipo === "recarga" ? "+" : "-"} R$ ${last.valor.toFixed(2)} - ${last.descricao ?? ""}`
        );
      } else {
        setUltimaMovimentacao("Nenhuma movimentação");
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Erro ao carregar carteira";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { saldo, ultimaMovimentacao, loading, error, refetch: fetch };
}

interface UseRechargeResult {
  realizarRecarga: (valor: number) => Promise<RecargaResponse>;
  loading: boolean;
  error: string | null;
}

export function useRecharge(): UseRechargeResult {
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
    []
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
  const [extrato, setExtrato] = useState<ExtratoResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getStatement({ page, size });
      setExtrato(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Erro ao carregar extrato";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [page, size]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { extrato, loading, error, refetch: fetch };
}
