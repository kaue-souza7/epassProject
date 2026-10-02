import type { NavigatorScreenParams } from "@react-navigation/native";
import type { GabaritoData } from "./gabarito";

export type ResponsavelStackParamList = {
  SelectStudent: undefined;
  HomeTabs: undefined;
  Boletim: undefined;
  BoletimAnual: undefined;
  Agenda: undefined;
  Wallet: undefined;
  Statement: undefined;
  Recharge: undefined;
  LiberarAluno: undefined;
  AtenaChat: undefined;
  CarteirinhaDigital: undefined;
  Cantina: undefined;
  MontarLanche: undefined;
  PersonalizarSemana: { diaSemana?: string } | undefined;
  PedidoStatus: { pedidoId: string };
  PedidoHistorico: undefined;
  OcorrenciaDetalhe: { ocorrenciaId: string };
  EditarPerfil: undefined;
  Notificacoes: undefined;
  SolicitarDocumentos: undefined;
  Acessibilidade: undefined;
};

export type ProfessorTabParamList = {
  Resumo: undefined;
  Modulos: undefined;
  Perfil: undefined;
};

export interface GabaritoAvaliacaoParams {
  alocacaoId: string;
  turmaId: string;
  turmaNome: string;
  disciplinaNome: string;
}

export interface GabaritoCadastroParams {
  avaliacaoId: string;
  avaliacaoTitulo: string;
  notaMaxima: number;
  alocacaoId: string;
  turmaId: string;
  turmaNome: string;
  disciplinaNome: string;
}

export interface GabaritoRevisaoParams {
  avaliacaoId: string;
  avaliacaoTitulo: string;
  notaMaxima: number;
  alocacaoId: string;
  turmaId: string;
  turmaNome: string;
  disciplinaNome: string;
  gabarito: GabaritoData;
  imageBase64: string;
}

export interface GabaritoProcessamentoParams {
  avaliacaoId: string;
  avaliacaoTitulo: string;
  notaMaxima: number;
  alocacaoId: string;
  turmaId: string;
  turmaNome: string;
  disciplinaNome: string;
}

export interface GabaritoResultadoParams {
  avaliacaoId: string;
  avaliacaoTitulo: string;
  notaMaxima: number;
  alocacaoId: string;
  turmaId: string;
  turmaNome: string;
  disciplinaNome: string;
  gabarito: GabaritoData;
  matriculaId: string;
  alunoNome: string;
  respostasAluno: (string | null)[];
}

export type ProfessorStackParamList = {
  ProfessorTabs: NavigatorScreenParams<ProfessorTabParamList>;
  ClassesList: undefined;
  GabaritoHome: undefined;
  GabaritoTurma: undefined;
  GabaritoAvaliacao: GabaritoAvaliacaoParams;
  GabaritoCadastro: GabaritoCadastroParams;
  GabaritoScanner: GabaritoCadastroParams;
  GabaritoProcessamento: GabaritoProcessamentoParams;
  GabaritoRevisao: GabaritoRevisaoParams;
  GabaritoResultado: GabaritoResultadoParams;
  TurmaAlunos: { turmaId: string; turmaNome: string; disciplinaNome: string; alocacaoId: string };
  LancarFrequencia: { turmaId: string; turmaNome: string; disciplinaNome: string; alocacaoId: string };
  LancarNotas: { turmaId: string; turmaNome: string; disciplinaNome: string; alocacaoId: string };
  EditarPerfil: undefined;
  Acessibilidade: undefined;
};
