export const PERFIS = {
  ADMIN: "admin",
  SECRETARIA: "secretaria",
  PROFESSOR: "professor",
  RESPONSAVEL: "responsavel",
} as const;

export const STATUS_MATRICULA = {
  ATIVA: "ativa",
  TRANSFERIDA: "transferida",
  CONCLUIDA: "concluida",
  CANCELADA: "cancelada",
} as const;

export const DIAS_SEMANA = [
  { value: "seg", label: "Segunda" },
  { value: "ter", label: "Terça" },
  { value: "qua", label: "Quarta" },
  { value: "qui", label: "Quinta" },
  { value: "sex", label: "Sexta" },
  { value: "sab", label: "Sábado" },
] as const;
