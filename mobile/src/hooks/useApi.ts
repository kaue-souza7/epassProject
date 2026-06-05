import { useState, useEffect, useCallback, useRef } from "react";
import axios from "axios";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseApiOptions {
  enabled?: boolean;
  errorMessage?: string;
}

interface UseApiReturn<T> extends UseApiState<T> {
  refetch: () => Promise<void>;
}

export function useApi<T>(
  fetchFn: (signal: AbortSignal) => Promise<T>,
  deps: React.DependencyList,
  options?: UseApiOptions
): UseApiReturn<T> {
  const { enabled = true, errorMessage = "Erro ao carregar dados" } = options ?? {};
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: enabled,
    error: null,
  });
  const mountedRef = useRef(true);
  const fetchRef = useRef(fetchFn);
  fetchRef.current = fetchFn;

  const run = useCallback(
    async (signal: AbortSignal) => {
      if (!enabled) {
        setState({ data: null, loading: false, error: null });
        return;
      }
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await fetchRef.current(signal);
        if (mountedRef.current) {
          setState({ data: result, loading: false, error: null });
        }
      } catch (err) {
        if (!mountedRef.current || axios.isCancel(err)) return;
        const message =
          err instanceof Error ? err.message : errorMessage;
        if (mountedRef.current) {
          setState((prev) => ({ ...prev, loading: false, error: message }));
        }
      }
    },
    [enabled, errorMessage]
  );

  useEffect(() => {
    mountedRef.current = true;
    const controller = new AbortController();
    run(controller.signal);
    return () => {
      mountedRef.current = false;
      controller.abort();
    };
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  const refetch = useCallback(async () => {
    const controller = new AbortController();
    await run(controller.signal);
  }, [run]);

  return { ...state, refetch };
}
