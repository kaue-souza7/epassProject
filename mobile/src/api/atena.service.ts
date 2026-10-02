import { fetch as expoFetch } from "expo/fetch";
import { api, getStoredAccessToken } from "./client";
import { getApiUrl } from "./config";

const API_URL = getApiUrl();

export interface MensagemIA {
  id: string;
  papel: "usuario" | "assistente";
  conteudo: string;
  intencao: string | null;
  codigo: string | null;
  criado_em: string;
}

export interface ConversaIA {
  id: string;
  titulo: string | null;
  criada_em: string;
  atualizada_em: string;
  total_mensagens: number;
}

export interface ChatRequest {
  message: string;
  aluno_selecionado_id?: string | null;
  conversa_id?: string | null;
  salvar?: boolean;
}

export type FrameAtena =
  | { tipo: "meta"; conversa_id: string }
  | { tipo: "delta"; texto: string }
  | { tipo: "erro"; erro: string; parcial: string }
  | {
      tipo: "done";
      resposta: {
        resposta: string;
        codigo: string;
        intencao: string | null;
        fatos_utilizados: number;
        modelo: string;
        perfil: string;
        latencia_ms: number;
        alertas_guardrails: string[];
        sugestoes: string[];
      };
    };

/**
 * Diagnóstico do assistente, visto pelo PERFIL autenticado.
 *
 * É este payload que decide o ponto de status do cabeçalho. Antes ele não era
 * consultado no mobile e o ponto ficava "Online" fixo — a tela afirmava que a
 * Atena estava no ar mesmo com o modelo fora, que é a pior forma de erro:
 * o usuário só descobre quando a pergunta falha.
 */
export interface HealthAtena {
  status: "ok" | "degraded" | "unavailable" | "desabilitado" | string;
  ai_enabled: boolean;
  ollama_alive: boolean;
  model_present: boolean;
  model: string;
  latencia_ms: number;
  intencoes_disponiveis: string[];
  sugestoes: string[];
}

/** Consultas de histórico: axios normal (o interceptor de refresh 401 vive lá). */
export const atenaService = {
  health: async (signal?: AbortSignal): Promise<HealthAtena> => {
    const { data } = await api.get<HealthAtena>("/ai/health", { signal });
    return data;
  },
  conversas: async (signal?: AbortSignal): Promise<ConversaIA[]> => {
    const { data } = await api.get<ConversaIA[]>("/ai/conversas", { signal });
    return data;
  },
  conversa: async (id: string, signal?: AbortSignal) => {
    const { data } = await api.get<{ conversa: ConversaIA; mensagens: MensagemIA[] }>(
      `/ai/conversas/${id}`,
      { signal },
    );
    return data;
  },
  criarConversa: async () => {
    const { data } = await api.post<ConversaIA>("/ai/conversas");
    return data;
  },
  excluirConversa: async (id: string) => {
    await api.delete(`/ai/conversas/${id}`);
  },
};

/**
 * Pergunta à Atena e consome a resposta em streaming (SSE).
 *
 * Usa `expo/fetch` e NÃO o `fetch` global: no React Native o `fetch` nativo é o
 * polyfill do whatwg, que não expõe `response.body` — sem corpo não há como ler
 * os pedaço a peçaço, e o usuário veria a tela parada por ~30s até a resposta
 * inteira chegar. O `expo/fetch` faz a requisição pelo módulo nativo e devolve
 * `body` como `ReadableStream` de verdade.
 *
 * Também não dá para usar `EventSource`: a rota é POST (o corpo leva
 * `aluno_selecionado_id` e `conversa_id`) e o EventSource não envia header
 * `Authorization`.
 *
 * Diferente das notificações (ver `contexts/NotificationsContext`), aqui NÃO há
 * reconexão automática: repetir a mesma pergunta custaria uma segunda
 * inferência no Ollama e gravaria o turno duas vezes no histórico.
 *
 * Devolve a função de cancelamento (usada ao sair da tela ou mandar outra
 * pergunta), que aborta a stream no servidor e devolve a vaga de concorrência.
 */
export function streamAtena(
  corpo: ChatRequest,
  onFrame: (frame: FrameAtena) => void,
  onFim: (erro?: string) => void,
): () => void {
  const controller = new AbortController();
  let encerrado = false;

  const conectar = async () => {
    try {
      const token = await getStoredAccessToken();
      if (encerrado) return;
      if (!token) {
        onFim("Sessão expirada. Entre novamente.");
        return;
      }

      const resposta = await expoFetch(`${API_URL}/ai/chat/stream`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(corpo),
        signal: controller.signal,
      });

      if (!resposta.ok || !resposta.body) {
        // 404 no streaming é o anti-IDOR: conversa de outra pessoa.
        if (resposta.status === 404) onFim("Conversa não encontrada.");
        else if (resposta.status === 401) onFim("Sessão expirada. Entre novamente.");
        else onFim("Não foi possível falar com a Atena agora.");
        return;
      }

      const reader = resposta.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let recebeuFinal = false;

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
            let frame: FrameAtena;
            try {
              frame = JSON.parse(payload) as FrameAtena;
            } catch {
              continue;
            }
            onFrame(frame);
            if (frame.tipo === "done" || frame.tipo === "erro") recebeuFinal = true;
          }
        }
      }

      if (!encerrado && !recebeuFinal) {
        onFim("A conexão caiu antes da Atena terminar a resposta.");
      }
      if (!encerrado) onFim();
    } catch (erro) {
      if (encerrado) return;
      const nome = (erro as { name?: string })?.name;
      if (nome === "AbortError") return;
      onFim("A conexão caiu antes da Atena terminar a resposta.");
    }
  };

  void conectar();

  return () => {
    encerrado = true;
    controller.abort();
  };
}
