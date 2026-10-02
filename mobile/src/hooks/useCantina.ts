import { useCallback, useState } from "react";
import { useApi } from "./useApi";
import { getApiErrorMessage } from "../api/errors";
import { useSelectedStudent } from "./useSelectedStudent";
import {
  getMenu,
  createOrder,
  getTodayOrder,
  getOrder,
  getMyOrders,
  getProgramacaoSemana,
  saveProgramacao,
  deleteProgramacao,
  getAutonomia,
  setAutonomia,
  cancelOrder,
  type MenuItem,
  type Pedido,
  type PedidoListItem,
  type PedidoCreate,
  type ProgramacaoSemana,
  type ProgramacaoCreate,
  type Programacao,
} from "../api/cantina.service";

// ── useMenu ──────────────────────────────────────────────────────

export function useMenu() {
  return useApi<MenuItem[]>(
    (signal) => getMenu(signal),
    [],
    { errorMessage: "Erro ao carregar cardápio" },
  );
}

// ── useTodayOrder ────────────────────────────────────────────────

export function useTodayOrder() {
  const { selectedChild } = useSelectedStudent();

  const { data, loading, error, refetch } = useApi<Pedido | null>(
    (signal) => selectedChild ? getTodayOrder(selectedChild.aluno_id, signal) : Promise.resolve(null),
    [selectedChild?.aluno_id],
    {
      enabled: !!selectedChild,
      errorMessage: "Erro ao carregar pedido do dia",
    },
  );

  return { pedido: data, loading, error, refetch };
}

// ── useOrderDetail ───────────────────────────────────────────────

export function useOrderDetail(orderId: string | null) {
  return useApi<Pedido>(
    (signal) => orderId ? getOrder(orderId, signal) : Promise.resolve({} as Pedido),
    [orderId],
    {
      enabled: !!orderId,
      errorMessage: "Erro ao carregar detalhes do pedido",
    },
  );
}

// ── useOrderHistory ──────────────────────────────────────────────

export function useOrderHistory(page = 1) {
  const { selectedChild } = useSelectedStudent();

  return useApi<{ items: PedidoListItem[]; total: number }>(
    (signal) =>
      getMyOrders(
        { page, size: 20, aluno_id: selectedChild?.aluno_id },
        signal,
      ),
    [page, selectedChild?.aluno_id],
    {
      enabled: !!selectedChild,
      errorMessage: "Erro ao carregar histórico",
    },
  );
}

// ── useCreateOrder ───────────────────────────────────────────────

export function useCreateOrder() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const criarPedido = useCallback(
    async (data: PedidoCreate): Promise<Pedido | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await createOrder(data);
        return result;
      } catch (err: unknown) {
        const message = getApiErrorMessage(err, "Erro ao criar pedido");
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { criarPedido, loading, error };
}

// ── useProgramacaoSemana ────────────────────────────────────────

export function useProgramacaoSemana() {
  const { selectedChild } = useSelectedStudent();

  const { data, loading, error, refetch } = useApi<ProgramacaoSemana>(
    (signal) => selectedChild ? getProgramacaoSemana(selectedChild.aluno_id, signal) : Promise.resolve({} as ProgramacaoSemana),
    [selectedChild?.aluno_id],
    {
      enabled: !!selectedChild,
      errorMessage: "Erro ao carregar programação",
    },
  );

  return { programacao: data, loading, error, refetch };
}

// ── useSaveProgramacao ──────────────────────────────────────────

export function useSaveProgramacao() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const salvar = useCallback(
    async (data: ProgramacaoCreate): Promise<Programacao | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await saveProgramacao(data);
        return result;
      } catch (err: unknown) {
        const message = getApiErrorMessage(err, "Erro ao salvar programação");
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { salvar, loading, error };
}

// ── useDeleteProgramacao ────────────────────────────────────────

export function useDeleteProgramacao() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const remover = useCallback(
    async (programacaoId: string): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        await deleteProgramacao(programacaoId);
        return true;
      } catch (err: unknown) {
        const message = getApiErrorMessage(err, "Erro ao remover programação");
        setError(message);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { remover, loading, error };
}

// ── useAutonomia ───────────────────────────────────────────────

export function useAutonomia() {
  const { selectedChild } = useSelectedStudent();

  const { data, loading, error, refetch } = useApi<{ aluno_id: string; autonomia_cantina: boolean }>(
    (signal) => selectedChild ? getAutonomia(selectedChild.aluno_id, signal) : Promise.resolve({ aluno_id: "", autonomia_cantina: false }),
    [selectedChild?.aluno_id],
    {
      enabled: !!selectedChild,
      errorMessage: "Erro ao carregar autonomia",
    },
  );

  return {
    autonomia: data?.autonomia_cantina ?? false,
    loading,
    error,
    refetch,
  };
}

// ── useToggleAutonomia ─────────────────────────────────────────

export function useToggleAutonomia() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = useCallback(
    async (alunoId: string, autonomia: boolean): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        await setAutonomia(alunoId, autonomia);
        return true;
      } catch (err: unknown) {
        const message = getApiErrorMessage(err, "Erro ao alterar autonomia");
        setError(message);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { toggle, loading, error };
}

// ── useCancelOrder ───────────────────────────────────────────

export function useCancelOrder() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cancelar = useCallback(
    async (orderId: string): Promise<Pedido | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await cancelOrder(orderId);
        return result;
      } catch (err: unknown) {
        const message = getApiErrorMessage(err, "Erro ao cancelar pedido");
        setError(message);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { cancelar, loading, error };
}
