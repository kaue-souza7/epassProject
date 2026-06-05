import { useApi } from "./useApi";
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
  const { data: events, loading, error, refetch } = useApi(
    (signal) => getEvents(params, signal),
    [params?.page, params?.size, params?.data_inicio, params?.data_fim],
    { errorMessage: "Erro ao carregar eventos" }
  );

  return { events, loading, error, refetch };
}

interface UseEventDetailResult {
  event: EventDetail | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useEventDetail(id: string | null): UseEventDetailResult {
  const { data: event, loading, error, refetch } = useApi(
    (signal) => getEvent(id!, signal),
    [id],
    { enabled: !!id, errorMessage: "Erro ao carregar evento" }
  );

  return { event, loading, error, refetch };
}
