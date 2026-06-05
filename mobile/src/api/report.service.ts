import { api } from "./client";
import type {
  ReportCard,
  ReportCardAnnual,
  FrequencyReport,
  SchoolHistory,
  EnrollmentCertificate,
  PaymentReceipt,
  EvolutionData,
  DocumentPdf,
} from "../types/responsavel";

export async function getReportCard(
  enrollmentId: string,
  bimestre: number,
  signal?: AbortSignal
): Promise<ReportCard> {
  const { data } = await api.get<ReportCard>(
    `/reports/report-card/${enrollmentId}`,
    { params: { bimestre }, signal }
  );
  return data;
}

export async function getAnnualReport(
  enrollmentId: string,
  signal?: AbortSignal
): Promise<ReportCardAnnual> {
  const { data } = await api.get<ReportCardAnnual>(
    `/reports/report-card/${enrollmentId}/annual`,
    { signal }
  );
  return data;
}

export async function getFrequencyReport(
  enrollmentId: string,
  startDate?: string,
  endDate?: string
): Promise<FrequencyReport> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  const { data } = await api.get<FrequencyReport>(
    `/reports/frequency/${enrollmentId}`,
    { params }
  );
  return data;
}

export async function getSchoolHistory(
  studentId: string
): Promise<SchoolHistory> {
  const { data } = await api.get<SchoolHistory>(
    `/reports/school-history/${studentId}`
  );
  return data;
}

export async function getEnrollmentCertificate(
  enrollmentId: string
): Promise<EnrollmentCertificate> {
  const { data } = await api.get<EnrollmentCertificate>(
    `/reports/enrollment-certificate/${enrollmentId}`
  );
  return data;
}

export async function getPaymentReceipt(
  movementId: string
): Promise<PaymentReceipt> {
  const { data } = await api.get<PaymentReceipt>(
    `/reports/payment-receipt/${movementId}`
  );
  return data;
}

export async function getEvolutionData(
  enrollmentId: string
): Promise<EvolutionData> {
  const { data } = await api.get<EvolutionData>(
    `/reports/evolution/${enrollmentId}`
  );
  return data;
}

export async function generatePdf(
  tipo: string,
  ids: {
    matricula_id?: string;
    aluno_id?: string;
    movimento_id?: string;
  }
): Promise<DocumentPdf> {
  const params: Record<string, string> = { tipo };
  if (ids.matricula_id) params.matricula_id = ids.matricula_id;
  if (ids.aluno_id) params.aluno_id = ids.aluno_id;
  if (ids.movimento_id) params.movimento_id = ids.movimento_id;
  const { data } = await api.post<DocumentPdf>("/reports/generate-pdf", null, {
    params,
  });
  return data;
}

export const REPORT_ITEMS = [
  {
    id: "boletim_anual",
    title: "Boletim Anual",
    description: "Notas e médias por bimestre",
    icon: "school",
    section: "academic",
  },
  {
    id: "boletim_bimestral",
    title: "Boletim Bimestral",
    description: "Notas por bimestre individual",
    icon: "document-text",
    section: "academic",
  },
  {
    id: "frequencia",
    title: "Frequência",
    description: "Relatório de presenças e faltas",
    icon: "calendar-check",
    section: "academic",
  },
  {
    id: "historico_escolar",
    title: "Histórico Escolar",
    description: "Histórico completo do aluno",
    icon: "time",
    section: "academic",
  },
  {
    id: "declaracao_matricula",
    title: "Declaração de Matrícula",
    description: "Comprovante de matrícula",
    icon: "document-text",
    section: "academic",
  },
  {
    id: "comprovante_pagamento",
    title: "Comprovante de Pagamento",
    description: "Recibos de mensalidades",
    icon: "card",
    section: "financial",
  },
  {
    id: "extrato_financeiro",
    title: "Extrato Financeiro",
    description: "Histórico de pagamentos",
    icon: "wallet",
    section: "financial",
  },
  {
    id: "evolucao",
    title: "Evolução Acadêmica",
    description: "Desempenho por bimestre",
    icon: "trending-up",
    section: "performance",
  },
] as const;
