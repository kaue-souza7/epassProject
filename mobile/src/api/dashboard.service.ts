import { api } from "./client";
import type { DashboardResponsavel } from "../types/responsavel";

export async function getDashboard(): Promise<DashboardResponsavel> {
  const { data } = await api.get<DashboardResponsavel>("/dashboard/responsavel");
  return data;
}
