import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, MessageCircle, Plus, Send, Sparkles, Trash2, User, X } from "lucide-react";
import { atenaApi, streamAtena, type MensagemIA } from "../../api/atena";
import { studentsApi } from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { PageHeader } from "../../components/layout/PageHeader";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { clsx } from "clsx";

/**
 * Mensagem na tela. `parcial` é o texto que ainda está chegando: enquanto a
 * inferência roda, a última bolha da Atena cresce a cada `delta`.
 */
interface Bolha {
  id: string;
  papel: "usuario" | "assistente";
  texto: string;
  emVoo?: boolean;
  erro?: boolean;
}

/**
 * Texto de abertura por perfil.
 *
 * Fica aqui, e não no backend, porque é a PRIMEIRA tela que o usuário vê e
 * precisa existir antes de ele perguntar qualquer coisa (a Atena ainda não
 * respondeu nada). As sugestões que a Atena oferece depois de responder vêm de
 * `/ai/health`; estas são o convite inicial.
 */
const ABERTURA: Record<string, string> = {
  responsavel:
    "Pergunte sobre notas, média, faltas, ocorrências, avisos, Carteira, lanches ou documentos dos seus filhos.",
  professor:
    "Pergunte sobre suas turmas: médias, frequência, avaliações sem nota, ocorrências ou prazos de boletim.",
  secretaria:
    "Pergunte sobre matrículas, turmas, séries, documentos, avisos, ocorrências ou a cantina.",
  admin:
    "Pergunte sobre matrículas, turmas, séries, documentos, avisos, ocorrências, cantina ou corpo docente.",
  coordenador:
    "Pergunte sobre turmas em risco, alunos que precisam de atenção, ocorrências abertas ou o panorama da escola.",
  cantineiro:
    "Pergunte sobre os pedidos de hoje, o cardápio, o estoque ou o saldo na carteira do aluno.",
};

const ROTULO_ABERTURA: Record<string, string> = {
  responsavel: "Aluno em foco",
  professor: "Turma em foco",
  secretaria: "Visão da secretaria",
  admin: "Visão da escola",
  coordenador: "Visão pedagógica",
  cantineiro: "Visão do balcão",
};

function paraBolhas(mensagens: MensagemIA[]): Bolha[] {
  return mensagens.map((m) => ({ id: m.id, papel: m.papel, texto: m.conteudo }));
}

export function AtenaChat() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const perfil = user?.perfil ?? "";

  const [conversaId, setConversaId] = useState<string | null>(null);
  const [conversaAberta, setConversaAberta] = useState<string | null>(null);
  // `aberta` = o usuário escolheu essa conversa na lista agora. Enquanto é
  // falso, quem manda na tela é o stream, não o servidor.
  const [aberta, setAberta] = useState(false);

  const [alunoId, setAlunoId] = useState<string>("");
  const [bolhas, setBolhas] = useState<Bolha[]>([]);
  const [texto, setTexto] = useState("");
  const [sugestoes, setSugestoes] = useState<string[]>([]);
  const [pensando, setPensando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const fimRef = useRef<HTMLDivElement>(null);
  const cancelarRef = useRef<(() => void) | null>(null);

  // Só o responsável tem filhos vinculados; para os demais perfis a pergunta é
  // respondida sem "aluno em foco". Pedir `/students/my-children` para um
  // professor, além de inútil, é uma chamada que volta 403.
  const ehResponsavel = perfil === "responsavel";

  const { data: filhos } = useQuery({
    queryKey: ["my-children"],
    queryFn: studentsApi.myChildren,
    enabled: ehResponsavel,
  });

  // O health traz o status real e as sugestões do perfil. É ele que decide se
  // a Atena aparece "Online" no cabeçalho ou "Indisponível" — antes disso o
  // mobile mostrava "Online" fixo, mentindo quando o modelo estava fora.
  const { data: saude } = useQuery({
    queryKey: ["atena-health"],
    queryFn: atenaApi.health,
    refetchInterval: 60_000,
  });

  const disponivel = saude ? saude.status === "ok" || saude.status === "degraded" : true;

  // Antes da primeira resposta, os chips vêm do health — o usuário descobre o
  // que dá para perguntar sem precisar mandar uma pergunta primeiro.
  const chips = sugestoes.length > 0 ? sugestoes : (saude?.sugestoes ?? []);

  const { data: conversas } = useQuery({
    queryKey: ["atena-conversas"],
    queryFn: atenaApi.conversas,
  });

  const {
    data: aberto,
    isLoading: carregandoConversa,
  } = useQuery({
    queryKey: ["atena-conversa", conversaAberta],
    queryFn: () => atenaApi.conversa(conversaAberta as string),
    enabled: !!conversaAberta,
  });

  // Só converte servidor -> tela, e apenas para a conversa que o usuário
  // ABRIU na lista. Se a tela recarregasse o snapshot a cada pergunta, um
  // `aberto` defasado (o fetch dispara no `meta`, antes do turno ser gravado)
  // apagaria da tela a resposta que acabou de chegar.
  useEffect(() => {
    if (aberto && aberta && aberto.conversa.id === conversaAberta && !pensando) {
      setBolhas(paraBolhas(aberto.mensagens));
    }
  }, [aberto, aberta, conversaAberta, pensando]);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [bolhas]);

  // Sai da tela = cancela a inferência. Sem isso, a stream do backend fica
  // segurando a única vaga de concorrência do Ollama até o timeout.
  useEffect(() => () => cancelarRef.current?.(), []);

  const nomeDoAluno = useMemo(
    () => filhos?.find((f) => f.id === alunoId)?.nome ?? null,
    [filhos, alunoId],
  );

  const perguntar = (pergunta: string) => {
    const limpa = pergunta.trim();
    if (!limpa || pensando) return;

    cancelarRef.current?.();
    setAberta(false);
    setErro(null);
    setTexto("");
    setPensando(true);
    setSugestoes([]);

    const idUsuario = `u-${Date.now()}`;
    const idBot = `a-${Date.now()}`;
    setBolhas((prev) => [
      ...prev,
      { id: idUsuario, papel: "usuario", texto: limpa },
      { id: idBot, papel: "assistente", texto: "", emVoo: true },
    ]);

    const cancelar = streamAtena(
      {
        message: limpa,
        aluno_selecionado_id: alunoId || null,
        conversa_id: conversaId,
        salvar: true,
      },
      (frame) => {
        if (frame.tipo === "meta") {
          setConversaId(frame.conversa_id);
        } else if (frame.tipo === "delta") {
          setBolhas((prev) =>
            prev.map((b) => (b.id === idBot ? { ...b, texto: b.texto + frame.texto } : b)),
          );
        } else if (frame.tipo === "done") {
          // O `done` é AUTORITATIVO: o backend pode ter cortado um número
          // inventado nos guardrails, e o texto dos deltas ainda é o pré-corte.
          setBolhas((prev) =>
            prev.map((b) =>
              b.id === idBot
                ? { ...b, texto: frame.resposta.resposta, emVoo: false }
                : b,
            ),
          );
          setSugestoes(frame.resposta.sugestoes ?? []);
        } else if (frame.tipo === "erro") {
          setBolhas((prev) =>
            prev.map((b) =>
              b.id === idBot
                ? {
                    ...b,
                    // O parcial mostra o que a Atena já dizia antes de falhar.
                    texto: frame.parcial || "Não consegui responder.",
                    emVoo: false,
                    erro: true,
                  }
                : b,
            ),
          );
          setErro(frame.erro);
        }
      },
      (erroFinal) => {
        setPensando(false);
        cancelarRef.current = null;
        if (erroFinal) setErro(erroFinal);
        queryClient.invalidateQueries({ queryKey: ["atena-conversas"] });
        queryClient.invalidateQueries({ queryKey: ["atena-conversa"] });
      },
    );
    cancelarRef.current = cancelar;
  };

  const novaConversa = () => {
    cancelarRef.current?.();
    cancelarRef.current = null;
    setConversaId(null);
    setConversaAberta(null);
    setAberta(false);
    setBolhas([]);
    setSugestoes([]);
    setErro(null);
    setPensando(false);
  };

  const abrirConversa = (id: string) => {
    cancelarRef.current?.();
    cancelarRef.current = null;
    setPensando(false);
    setErro(null);
    setConversaId(id);
    setConversaAberta(id);
    setAberta(true);
  };

  const apagarConversa = async (id: string) => {
    await atenaApi.excluirConversa(id);
    if (id === conversaId || id === conversaAberta) novaConversa();
    queryClient.invalidateQueries({ queryKey: ["atena-conversas"] });
  };

  return (
    <div className="flex flex-col h-full">
      <Breadcrumb items={[{ label: "Atena" }]} />
      <PageHeader
        title="Atena"
        description="Assistente da escola"
        showNew={false}
      >
        <span
          className={clsx(
            "mr-2 inline-flex items-center gap-1.5 text-xs",
            disponivel
              ? "text-emerald-600 dark:text-emerald-400"
              : "text-amber-600 dark:text-amber-400",
          )}
          title={
            saude
              ? `Modelo: ${saude.model} · ${saude.latencia_ms}ms`
              : "Verificando o assistente…"
          }
        >
          <span
            className={clsx(
              "h-2 w-2 rounded-full",
              disponivel ? "bg-emerald-500" : "bg-amber-500",
            )}
          />
          {saude
            ? disponivel
              ? "Online"
              : saude.status === "desabilitado"
                ? "Desativada"
                : "Indisponível"
            : "…"}
        </span>
        <Button variant="outline" size="sm" onClick={novaConversa} disabled={pensando}>
          <Plus className="h-4 w-4 mr-1" />
          Nova conversa
        </Button>
      </PageHeader>

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4 flex-1 min-h-0">
        {/* Lateral: contexto em foco (só responsável) + conversas anteriores */}
        <div className="flex flex-col gap-4 min-h-0">
          {ehResponsavel ? (
            <Card padding="sm">
              <label
                htmlFor="atena-aluno"
                className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1"
              >
                {ROTULO_ABERTURA.responsavel}
              </label>
              <select
                id="atena-aluno"
                value={alunoId}
                onChange={(e) => setAlunoId(e.target.value)}
                className="w-full px-2 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-black dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Nenhum (todos os filhos)</option>
                {filhos?.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.nome}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                A Atena só responde sobre os filhos vinculados a você.
              </p>
            </Card>
          ) : (
            <Card padding="sm">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                {ROTULO_ABERTURA[perfil] ?? "Seu escopo"}
              </p>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                A Atena responde apenas sobre o que o seu perfil pode ver.
              </p>
            </Card>
          )}

          <Card padding="none" className="flex-1 min-h-0 overflow-hidden flex flex-col">
            <p className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-gray-400 border-b border-gray-200 dark:border-gray-700">
              Conversas
            </p>
            <div className="overflow-y-auto p-2 flex-1">
              {conversas?.length === 0 && (
                <p className="px-2 py-4 text-xs text-gray-500 dark:text-gray-400">
                  Nenhuma conversa ainda.
                </p>
              )}
              {conversas?.map((c) => (
                <div
                  key={c.id}
                  className={clsx(
                    "group flex items-center gap-1 rounded-lg px-2 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800",
                    c.id === conversaAberta && "bg-primary-50 dark:bg-primary-900/20",
                  )}
                  onClick={() => abrirConversa(c.id)}
                >
                  <MessageCircle className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-gray-900 dark:text-gray-100 truncate">
                      {c.titulo || "Conversa sem título"}
                    </p>
                    <p className="text-xs text-gray-400">
                      {new Date(c.atualizada_em).toLocaleDateString("pt-BR")}
                    </p>
                  </div>
                  <button
                    type="button"
                    aria-label="Excluir conversa"
                    className="opacity-0 group-hover:opacity-100 focus:opacity-100 text-gray-400 hover:text-danger-500 transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      void apagarConversa(c.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Conversa */}
        <Card padding="none" className="flex flex-col min-h-[500px]">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {carregandoConversa && (
              <div className="flex justify-center py-8"><Spinner size="lg" /></div>
            )}

            {!carregandoConversa && bolhas.length === 0 && (
              <div className="text-center py-12">
                <Sparkles className="h-10 w-10 text-primary-500 mx-auto mb-3" />
                <p className="text-gray-600 dark:text-gray-300 mb-1">
                  Olá{user?.nome ? `, ${user.nome.split(" ")[0]}` : ""}! Sou a Atena.
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                  {ABERTURA[perfil] ?? ABERTURA.responsavel}
                  {nomeDoAluno ? ` de ${nomeDoAluno}` : ""}.
                </p>
              </div>
            )}

            {/* Assistente fora do ar: a conversa continua no histórico, mas
                avisar é melhor que deixar o usuário descobrir que a pergunta
                foi descartada. */}
            {!disponivel && bolhas.length === 0 && (
              <div className="px-4 py-2 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 text-sm text-center">
                A Atena está sem resposta no momento. As conversas anteriores
                continuam disponíveis na lista ao lado.
              </div>
            )}

            {bolhas.map((b) => (
              <div
                key={b.id}
                className={clsx("flex gap-2", b.papel === "usuario" && "flex-row-reverse")}
              >
                <div
                  className={clsx(
                    "h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0",
                    b.papel === "usuario"
                      ? "bg-gray-200 dark:bg-gray-700"
                      : "bg-primary-500 text-white",
                  )}
                >
                  {b.papel === "usuario" ? (
                    <User className="h-4 w-4 text-gray-600 dark:text-gray-300" />
                  ) : (
                    <Bot className="h-4 w-4" />
                  )}
                </div>
                <div
                  className={clsx(
                    "max-w-[75%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap",
                    b.papel === "usuario"
                      ? "bg-primary-500 text-white rounded-tr-sm"
                      : b.erro
                        ? "bg-danger-50 text-danger-600 dark:bg-danger-900/20 dark:text-danger-300 rounded-tl-sm"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-sm",
                  )}
                >
                  {b.texto || (b.emVoo ? <span className="opacity-60">…</span> : null)}
                </div>
              </div>
            ))}
            <div ref={fimRef} />
          </div>

          {erro && (
            <div className="px-4 py-2 bg-danger-50 dark:bg-danger-900/20 text-danger-600 dark:text-danger-300 text-sm flex items-start gap-2">
              <span className="flex-1">{erro}</span>
              <button type="button" onClick={() => setErro(null)} aria-label="Fechar aviso">
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          {chips.length > 0 && !pensando && (
            <div className="px-4 pb-2 flex flex-wrap gap-2">
              {chips.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => perguntar(s)}
                  className="text-xs px-3 py-1.5 rounded-full border border-primary-500 text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          <form
            className="border-t border-gray-200 dark:border-gray-700 p-3 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              perguntar(texto);
            }}
          >
            <input
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              maxLength={500}
              placeholder={disponivel ? "Pergunte sobre a escola…" : "A Atena está indisponível agora"}
              disabled={!disponivel}
              className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-transparent text-black dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
            />
            <Button type="submit" disabled={!texto.trim() || pensando || !disponivel} loading={pensando}>
              {!pensando && <Send className="h-4 w-4" />}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
