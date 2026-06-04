import { useState, useEffect, useCallback } from "react";
import { getEvents, getEvent } from "../api/agenda.service";
import type { EventsParams } from "../api/agenda.service";
import type { AgendaEvent, EventDetail } from "../types/responsavel";
import type { PaginatedResponse } from "../types";

interface UseEventsResult {
  events: PaginatedResponse<AgendaEvent> | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useEvents(params?: EventsParams): UseEventsResult {
  const [events, setEvents] = useState<PaginatedResponse<AgendaEvent> | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getEvents(params);
      setEvents(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Erro ao carregar eventos";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [params?.page, params?.size, params?.data_inicio, params?.data_fim]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { events, loading, error, refetch: fetch };
}

interface UseEventDetailResult {
  event: EventDetail | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useEventDetail(id: string | null): UseEventDetailResult {
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    if (!id) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getEvent(id);
      setEvent(result);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Erro ao carregar evento";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { event, loading, error, refetch: fetch };
}
