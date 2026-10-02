import axios from "axios";

interface ApiErrorBody {
  message?: string;
  detail?: string | Array<{ msg?: string }>;
}

/**
 * Extrai a mensagem de erro legível do backend.
 *
 * O backend responde erros de negócio como `{ error, message }` e erros de
 * validação do FastAPI como `{ detail: [...] }`. Sem isso, o app exibia apenas
 * "Request failed with status code 422" e escondia regras como
 * "Saldo insuficiente" ou "O prazo para cancelamento expirou".
 */
export function getApiErrorMessage(err: unknown, fallback = "Erro inesperado"): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as ApiErrorBody | undefined;
    if (data?.message) return data.message;
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (first?.msg) return String(first.msg);
    }
    if (err.code === "ECONNABORTED") {
      return "Tempo de conexão esgotado. Tente novamente.";
    }
    if (!err.response) {
      return "Sem conexão com o servidor.";
    }
    if (err.response.status === 401) return "Sessão expirada. Faça login novamente.";
    if (err.response.status === 403) return "Você não tem permissão para esta ação.";
    if (err.response.status === 404) return "Recurso não encontrado.";
    return fallback;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
