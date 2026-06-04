import { api } from "./client";
import type { ReportCard, ReportCardAnnual } from "../types/responsavel";

export async function getReportCard(
  enrollmentId: string,
  bimestre: number
): Promise<ReportCard> {
  const { data } = await api.get<ReportCard>(
    `/reports/report-card/${enrollmentId}`,
    { params: { bimestre } }
  );
  return data;
}

export async function getAnnualReport(
  enrollmentId: string
): Promise<ReportCardAnnual> {
  const { data } = await api.get<ReportCardAnnual>(
    `/reports/report-card/${enrollmentId}/annual`
  );
  return data;
}
