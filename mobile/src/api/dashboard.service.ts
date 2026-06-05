import { api } from "./client";
import type { DashboardResponsavel } from "../types/responsavel";

export async function getDashboard(signal?: AbortSignal): Promise<DashboardResponsavel> {
  const { data } = await api.get<DashboardResponsavel>("/dashboard/responsavel", { signal });
  return data;
}
