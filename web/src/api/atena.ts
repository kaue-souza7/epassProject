import { api, getAccessToken } from "./client";

const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

export interface FonteIA {
  intencao: string | null;
  fatos_utilizados: number;
  modelo: string;
  latencia_ms: number;
  tokens: number;
  alertas_guardrails: string[];
}

export interface ChatResponse {
  resposta: string;
  codigo: string;
  fonte: FonteIA;
  sugestoes: string[];
  conversa_id: string | null;
  mensagem_id: string | null;
}

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

export interface ConversaComMensagens {
  conversa: ConversaIA;
  mensagens: MensagemIA[];
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
 * `status` é o que o cabeçalho mostra. `sugestoes` e `intencoes_disponiveis`
 * são por perfil: o backend devolve o catálogo daquele usuário, então a tela
 * nunca precisa saber as regras de mapeamento — só exibe o que veio.
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

export const atenaApi = {
  health: async () => {
    const { data } = await api.get<HealthAtena>("/ai/health");
    return data;
  },
  conversas: async () => {
    const { data } = await api.get<ConversaIA[]>("/ai/conversas");
    return data;
  },
  criarConversa: async () => {
    const { data } = await api.post<ConversaIA>("/ai/conversas");
    return data;
  },
  conversa: async (id: string) => {
    const { data } = await api.get<ConversaComMensagens>(`/ai/conversas/${id}`);
    return data;
  },
  excluirConversa: async (id: string) => {
    await api.delete(`/ai/conversas/${id}`);
  },
  chat: async (corpo: ChatRequest) => {
    const { data } = await api.post<ChatResponse>("/ai/chat", corpo);
    return data;
  },
};

/**
 * Envia a pergunta e consome o SSE de resposta.
 *
 * Usa `fetch` (e não EventSource) por dois motivos: `EventSource` não aceita
 * header `Authorization`, e a rota é POST (o corpo tem o `aluno_selecionado_id`
 * e o `conversa_id`). O padrão é o mesmo de `api/realtime.ts`.
 *
 * Diferença importante para as notificações: aqui NÃO há reconexão. Uma
 * pergunta é uma inferência cara e única; repetir a mesma requisição quando o
 * usuário cair no meio custaria uma segunda inferência e gravaria o turno duas
 * vezes. Se a conexão cair, o partial vira erro na tela e o usuário decide.
 *
 * Retorna a função de cancelamento, para abortar a inferência quando o
 * usuário manda outra pergunta ou sai da tela.
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
      const token = getAccessToken();
      if (!token) {
        onFim("Sessão expirada. Entre novamente.");
        return;
      }
      const resposta = await fetch(`${API_URL}/ai/chat/stream`, {
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
        // 404 aqui é o anti-IDOR do backend: conversa de outra pessoa.
        if (resposta.status === 404) {
          onFim("Conversa não encontrada.");
        } else if (resposta.status === 401) {
          onFim("Sessão expirada. Entre novamente.");
        } else {
          onFim("Não foi possível falar com a Atena agora.");
        }
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
            if (frame.tipo === "done" || frame.tipo === "erro") {
              recebeuFinal = true;
            }
          }
        }
      }

      if (!encerrado && !recebeuFinal) {
        onFim("A conexão caiu antes da Atena terminar a resposta.");
      }
      if (!encerrado) onFim();
    } catch (erro) {
      if (encerrado || (erro instanceof DOMException && erro.name === "AbortError")) return;
      onFim("A conexão caiu antes da Atena terminar a resposta.");
    }
  };

  void conectar();

  return () => {
    encerrado = true;
    controller.abort();
  };
}
