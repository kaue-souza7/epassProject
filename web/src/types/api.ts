export interface ApiError {
  error: string;
  message: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface User {
  id: string;
  nome: string;
  email: string;
  perfil: "admin" | "secretaria" | "professor" | "responsavel";
  ativo: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
