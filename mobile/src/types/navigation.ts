import type { NavigatorScreenParams } from "@react-navigation/native";

export type ResponsavelStackParamList = {
  SelectStudent: undefined;
  HomeTabs: undefined;
  Boletim: undefined;
  BoletimAnual: undefined;
  Agenda: undefined;
  Wallet: undefined;
  Statement: undefined;
  Recharge: undefined;
};

export type ProfessorTabParamList = {
  Resumo: undefined;
  Modulos: undefined;
  Perfil: undefined;
};

export type ProfessorStackParamList = {
  ProfessorTabs: NavigatorScreenParams<ProfessorTabParamList>;
  TurmaAlunos: { turmaId: string; turmaNome: string; disciplinaNome: string; alocacaoId: string };
  LancarFrequencia: { turmaId: string; turmaNome: string; disciplinaNome: string; alocacaoId: string };
  LancarNotas: { turmaId: string; turmaNome: string; disciplinaNome: string; alocacaoId: string };
};
