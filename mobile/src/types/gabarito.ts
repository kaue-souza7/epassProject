export interface GabaritoData {
  avaliacaoId: string;
  questoes: number;
  respostasCorretas: string[];
  createdAt: string;
}

export interface DetectedAnswers {
  questoes: number;
  respostas: (string | null)[];
}

export interface MarkerResult {
  name: string;
  x: number;
  y: number;
  expectedCx: number;
  expectedCy: number;
  brightness: number;
  found: boolean;
}

export interface DetectionResult {
  markers: MarkerResult[];
  allFound: boolean;
  foundCount: number;
}

export interface CorrecaoResult {
  alunoNome: string;
  matriculaId: string;
  questoes: number;
  acertos: number;
  erros: number;
  nota: number;
  respostasAluno: (string | null)[];
  respostasCorretas: string[];
}
