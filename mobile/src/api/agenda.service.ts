import { api } from "./client";
import type { AgendaEvent, EventDetail } from "../types/responsavel";
import type { PaginatedResponse } from "../types";

export interface EventsParams {
  page?: number;
  size?: number;
  data_inicio?: string;
  data_fim?: string;
}

export async function getEvents(
  params?: EventsParams,
  signal?: AbortSignal
): Promise<PaginatedResponse<AgendaEvent>> {
  const { data } = await api.get<PaginatedResponse<AgendaEvent>>(
    "/agenda/events",
    { params, signal }
  );
  return data;
}

export async function getEvent(id: string, signal?: AbortSignal): Promise<EventDetail> {
  const { data } = await api.get<EventDetail>(`/agenda/events/${id}`, { signal });
  return data;
}
