export type Perfil = "admin" | "secretaria" | "professor" | "responsavel";

export interface User {
  id: string;
  nome: string;
  email: string;
  perfil: Perfil;
  ativo: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface MeResponse extends User {}

export interface ApiError {
  error: string;
  message: string;
  detail?: string;
}

export type SituacaoAluno =
  | "aprovado"
  | "reprovado"
  | "recuperacao"
  | "aprovado_pos_recuperacao"
  | "reprovado_pos_recuperacao";

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
