import { useCallback, useEffect, useState } from "react";
import { useApi } from "./useApi";
import { getApiErrorMessage } from "../api/errors";
import {
  getAvisos,
  getNotificacoes,
  getNotificacoesNaoLidas,
  marcarAvisoLido,
  marcarNotificacaoLida,
  marcarTodasNotificacoesLidas,
  type Aviso,
  type Notificacao,
  type Paginated,
  type StatusAviso,
} from "../api/communication.service";

export function useAvisos(status?: StatusAviso, size = 50) {
  return useApi<Paginated<Aviso>>(
    (signal) => getAvisos({ page: 1, size, status }, signal),
    [status, size],
    { errorMessage: "Erro ao carregar avisos" },
  );
}

export function useNotificacoes(apenasNaoLidas = false, size = 50) {
  return useApi<Paginated<Notificacao>>(
    (signal) => getNotificacoes({ page: 1, size, apenas_nao_lidas: apenasNaoLidas }, signal),
    [apenasNaoLidas, size],
    { errorMessage: "Erro ao carregar notificações" },
  );
}

/** Contador de notificações não lidas com atualização periódica. */
export function useNotificacoesNaoLidas(intervalMs = 60000) {
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const carregar = useCallback(async (signal?: AbortSignal) => {
    try {
      const res = await getNotificacoesNaoLidas(signal);
      setTotal(res.total);
    } catch {
      // silencioso: badge não deve quebrar a UI
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void carregar(controller.signal);
    const timer = setInterval(() => void carregar(), intervalMs);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [carregar, intervalMs]);

  return { total, loading, recarregar: carregar };
}

export function useAvisoActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const marcarLido = useCallback(async (avisoId: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await marcarAvisoLido(avisoId);
      return true;
    } catch (err) {
      setError(getApiErrorMessage(err, "Erro ao marcar aviso como lido"));
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return { marcarLido, loading, error };
}

export function useNotificacaoActions() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const marcarLida = useCallback(async (id: string): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await marcarNotificacaoLida(id);
      return true;
    } catch (err) {
      setError(getApiErrorMessage(err, "Erro ao marcar notificação como lida"));
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const marcarTodasLidas = useCallback(async (): Promise<number | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await marcarTodasNotificacoesLidas();
      return res.marcadas;
    } catch (err) {
      setError(getApiErrorMessage(err, "Erro ao marcar notificações como lidas"));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { marcarLida, marcarTodasLidas, loading, error };
}
