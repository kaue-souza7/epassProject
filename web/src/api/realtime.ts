import { getAccessToken } from "./client";

const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

export interface NotificacaoRealtime {
  id: string;
  tipo: string;
  titulo: string;
  mensagem: string;
  entidade_tipo: string | null;
  entidade_id: string | null;
  dados: Record<string, any> | null;
  created_at: string | null;
}

export interface EventoRealtime {
  evento: "notificacao" | string;
  notificacao: NotificacaoRealtime;
}

/**
 * Assina o stream SSE de notificações do usuário autenticado.
 *
 * Usa `fetch` (e não EventSource) para enviar o header Authorization, com
 * reconexão exponencial. Retorna uma função de cancelamento.
 */
export function subscribeNotificacoes(
  onEvento: (evento: EventoRealtime) => void,
  onStatus?: (conectado: boolean) => void,
): () => void {
  const controller = new AbortController();
  let tentativa = 0;
  let encerrado = false;

  const conectar = async () => {
    if (encerrado) return;
    const token = getAccessToken();
    if (!token) {
      setTimeout(conectar, 3000);
      return;
    }
    try {
      const resposta = await fetch(`${API_URL}/notificacoes/stream`, {
        headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
        signal: controller.signal,
      });
      if (!resposta.ok || !resposta.body) {
        throw new Error(`SSE falhou: ${resposta.status}`);
      }
      tentativa = 0;
      onStatus?.(true);
      const reader = resposta.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!encerrado) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocos = buffer.split("\n\n");
        buffer = blocos.pop() ?? "";
        for (const bloco of blocos) {
          for (const linha of bloco.split("\n")) {
            if (!linha.startsWith("data:")) continue;
            const payload = linha.slice(5).trim();
            if (!payload) continue;
            try {
              onEvento(JSON.parse(payload) as EventoRealtime);
            } catch {
              // ignora evento malformado
            }
          }
        }
      }
    } catch {
      // silencioso: tenta reconectar
    } finally {
      onStatus?.(false);
    }

    if (!encerrado) {
      tentativa = Math.min(tentativa + 1, 6);
      setTimeout(conectar, Math.min(1000 * 2 ** tentativa, 30000));
    }
  };

  void conectar();

  return () => {
    encerrado = true;
    controller.abort();
  };
}
