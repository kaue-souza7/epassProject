import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  avisosApi,
  type AvisoDetalhe,
  type AvisoMensagem,
  type CaixaAviso,
  type PublicoDisponivel,
  type StatusAviso,
} from "../../api/endpoints";
import { useAuth } from "../../contexts/AuthContext";
import { useToast } from "../../components/ui/Toast";
import { PageHeader } from "../../components/layout/PageHeader";
import { Breadcrumb } from "../../components/layout/Breadcrumb";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Input } from "../../components/ui/Input";
import { ErrorState } from "../../components/ui/ErrorState";
import { Skeleton } from "../../components/ui/Skeleton";
import {
  AlertTriangle,
  CheckCheck,
  MessageSquare,
  Search,
  Send,
  Users,
} from "lucide-react";

const MANAGE_ROLES = ["admin", "secretaria", "coordenador"];
const SENDER_ROLES = ["admin", "secretaria", "coordenador", "professor"];

const PRIORIDADE_LABEL: Record<string, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};

const PRIORIDADE_VARIANT: Record<string, "info" | "warning" | "danger"> = {
  baixa: "info",
  media: "warning",
  alta: "danger",
};

function PublicoChecklist({
  titulo,
  itens,
  selecionados,
  onToggle,
  vazio,
}: {
  titulo: string;
  itens: { id: string; primary: string; secondary?: string | null }[];
  selecionados: Set<string>;
  onToggle: (id: string) => void;
  vazio: string;
}) {
  const [filtro, setFiltro] = useState("");
  const visiveis = itens.filter((i) =>
    !filtro ||
    i.primary.toLowerCase().includes(filtro.toLowerCase()) ||
    (i.secondary ?? "").toLowerCase().includes(filtro.toLowerCase()),
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-xs font-medium text-gray-500 dark:text-gray-400">
          {titulo} ({selecionados.size} selecionado{selecionados.size !== 1 ? "s" : ""})
        </label>
        {itens.length > 6 && (
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-400" />
            <input
              className="pl-6 pr-2 py-1 text-xs bg-transparent border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 dark:text-gray-100 w-40"
              placeholder="Filtrar..."
              value={filtro}
              onChange={(e) => setFiltro(e.target.value)}
            />
          </div>
        )}
      </div>
      <div className="max-h-40 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg divide-y divide-gray-100 dark:divide-gray-800">
        {visiveis.length === 0 ? (
          <p className="px-3 py-3 text-xs text-gray-400">{vazio}</p>
        ) : (
          visiveis.map((item) => (
            <label
              key={item.id}
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/40"
            >
              <input
                type="checkbox"
                checked={selecionados.has(item.id)}
                onChange={() => onToggle(item.id)}
              />
              <span className="min-w-0 flex-1 truncate text-gray-700 dark:text-gray-200">
                {item.primary}
              </span>
              {item.secondary && (
                <span className="text-xs text-gray-400 flex-shrink-0">{item.secondary}</span>
              )}
            </label>
          ))
        )}
      </div>
    </div>
  );
}

function ComposerModal({
  open,
  onClose,
  publico,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  publico: PublicoDisponivel | undefined;
  onCreated: () => void;
}) {
  const { toast } = useToast();
  const [titulo, setTitulo] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [prioridade, setPrioridade] = useState("media");
  const [permiteRespostas, setPermiteRespostas] = useState(false);
  const [paraProfessores, setParaProfessores] = useState(false);
  const [paraResponsaveis, setParaResponsaveis] = useState(false);
  const [professores, setProfessores] = useState<Set<string>>(new Set());
  const [responsaveis, setResponsaveis] = useState<Set<string>>(new Set());
  const [turmas, setTurmas] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open) return;
    setTitulo("");
    setMensagem("");
    setPrioridade("media");
    setPermiteRespostas(false);
    setParaProfessores(false);
    setParaResponsaveis(false);
    setProfessores(new Set());
    setResponsaveis(new Set());
    setTurmas(new Set());
  }, [open]);

  const podeProfessores = publico?.pode_enviar_para_professores ?? false;

  const criar = useMutation({
    mutationFn: () =>
      avisosApi.create({
        titulo,
        mensagem,
        prioridade,
        permite_respostas: permiteRespostas,
        para_professores: podeProfessores && paraProfessores,
        professor_ids: podeProfessores ? [...professores] : [],
        para_responsaveis: paraResponsaveis,
        responsavel_ids: [...responsaveis],
        turma_ids: [...turmas],
      }),
    onSuccess: () => {
      toast("success", "Aviso publicado e notificações enviadas");
      onCreated();
      onClose();
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao publicar aviso");
    },
  });

  const semPublico =
    !paraProfessores &&
    professores.size === 0 &&
    !paraResponsaveis &&
    responsaveis.size === 0 &&
    turmas.size === 0;

  const toggle = (setter: React.Dispatch<React.SetStateAction<Set<string>>>) => (id: string) => {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <Modal open={open} title="Novo Aviso" onClose={onClose} size="lg">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (semPublico) {
            toast("warning", "Selecione pelo menos um destinatário");
            return;
          }
          criar.mutate();
        }}
      >
        <Input
          label="Título"
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          required
          minLength={3}
        />
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
            Mensagem
          </label>
          <textarea
            className="w-full px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
            rows={4}
            value={mensagem}
            onChange={(e) => setMensagem(e.target.value)}
            required
            minLength={3}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
              Prioridade
            </label>
            <select
              className="w-full px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
              value={prioridade}
              onChange={(e) => setPrioridade(e.target.value)}
            >
              <option value="baixa">Baixa</option>
              <option value="media">Média</option>
              <option value="alta">Alta</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200 sm:mt-6">
            <input
              type="checkbox"
              checked={permiteRespostas}
              onChange={(e) => setPermiteRespostas(e.target.checked)}
            />
            <MessageSquare className="h-4 w-4 text-primary-500" />
            Permitir respostas
          </label>
        </div>

        <div className="border-t border-gray-200 dark:border-gray-700 pt-4 space-y-4">
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Users className="h-4 w-4 text-primary-500" /> Destinatários
          </p>

          {podeProfessores && (
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
                <input
                  type="checkbox"
                  checked={paraProfessores}
                  onChange={(e) => setParaProfessores(e.target.checked)}
                />
                Todos os professores
              </label>
              {!paraProfessores && (
                <PublicoChecklist
                  titulo="Professores selecionados"
                  itens={(publico?.professores ?? []).map((p) => ({
                    id: p.id,
                    primary: p.nome,
                  }))}
                  selecionados={professores}
                  onToggle={toggle(setProfessores)}
                  vazio="Nenhum professor cadastrado"
                />
              )}
            </div>
          )}

          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
              <input
                type="checkbox"
                checked={paraResponsaveis}
                onChange={(e) => setParaResponsaveis(e.target.checked)}
              />
              {podeProfessores ? "Todos os responsáveis" : "Todos os responsáveis das minhas turmas"}
            </label>
            {!paraResponsaveis && (
              <PublicoChecklist
                titulo="Responsáveis selecionados"
                itens={(publico?.responsaveis ?? []).map((r) => ({
                  id: r.id,
                  primary: r.nome,
                  secondary: r.aluno_nome
                    ? `${r.aluno_nome}${r.turma_codigo ? ` · ${r.turma_codigo}` : ""}`
                    : null,
                }))}
                selecionados={responsaveis}
                onToggle={toggle(setResponsaveis)}
                vazio="Nenhum responsável disponível"
              />
            )}
          </div>

          <PublicoChecklist
            titulo="Turmas (responsáveis da turma)"
            itens={(publico?.turmas ?? []).map((t) => ({
              id: t.id,
              primary: t.codigo,
              secondary: t.nome,
            }))}
            selecionados={turmas}
            onToggle={toggle(setTurmas)}
            vazio="Nenhuma turma disponível"
          />
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" loading={criar.isPending} disabled={semPublico}>
            <Send className="h-4 w-4 mr-2" /> Publicar
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function MensagemBolha({ mensagem }: { mensagem: AvisoMensagem }) {
  const minha = mensagem.enviada_por_mim;
  return (
    <div className={`flex ${minha ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
          minha
            ? "bg-primary-500 text-white rounded-br-sm"
            : "bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-100 rounded-bl-sm"
        }`}
      >
        {!minha && (
          <p className="text-xs font-semibold opacity-80 mb-0.5">
            {mensagem.autor_nome ?? "Usuário"}
          </p>
        )}
        <p className="whitespace-pre-wrap">{mensagem.conteudo}</p>
        <p className={`text-[10px] mt-1 ${minha ? "text-white/70" : "text-gray-400"}`}>
          {new Date(mensagem.created_at).toLocaleString("pt-BR")}
          {minha && mensagem.lida_em ? " · lida" : ""}
          {!minha && !mensagem.lida_em ? " · não lida" : ""}
        </p>
      </div>
    </div>
  );
}

function DetailModal({
  avisoId,
  onClose,
}: {
  avisoId: string | null;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [resposta, setResposta] = useState("");
  const [destinoResposta, setDestinoResposta] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["aviso", avisoId],
    queryFn: () => avisosApi.getById(avisoId as string),
    enabled: !!avisoId,
  });

  const { data: mensagens } = useQuery({
    queryKey: ["aviso-mensagens", avisoId],
    queryFn: () => avisosApi.mensagens(avisoId as string),
    enabled: !!avisoId,
    refetchInterval: 30000,
  });

  const souAutor = data?.aviso.sou_autor ?? false;
  const podeGerenciar =
    souAutor || (!!user?.perfil && MANAGE_ROLES.includes(user.perfil));

  const marcarLido = useMutation({
    mutationFn: () => avisosApi.marcarLido(avisoId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["aviso", avisoId] });
      queryClient.invalidateQueries({ queryKey: ["avisos"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes-nao-lidas"] });
    },
  });

  // Marca como lido automaticamente ao abrir, se for destinatário pendente.
  useEffect(() => {
    if (!data) return;
    if (!data.aviso.sou_autor && !data.aviso.lido_por_mim) {
      marcarLido.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.aviso.id, data?.aviso.lido_por_mim]);

  const responder = useMutation({
    mutationFn: () =>
      avisosApi.responder(
        avisoId as string,
        resposta,
        souAutor ? destinoResposta || undefined : undefined,
      ),
    onSuccess: () => {
      setResposta("");
      queryClient.invalidateQueries({ queryKey: ["aviso-mensagens", avisoId] });
      queryClient.invalidateQueries({ queryKey: ["aviso", avisoId] });
      toast("success", "Resposta enviada");
    },
    onError: (err: any) => {
      toast("error", err?.response?.data?.message || "Erro ao responder");
    },
  });

  const arquivar = useMutation({
    mutationFn: () => avisosApi.arquivar(avisoId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["aviso", avisoId] });
      queryClient.invalidateQueries({ queryKey: ["avisos"] });
      toast("success", "Aviso arquivado");
    },
  });

  const detalhe: AvisoDetalhe | undefined = data;
  const naoLidasDestino = new Set(
    (mensagens ?? []).filter((m) => !m.enviada_por_mim && !m.lida_em).map((m) => m.id),
  );
  void naoLidasDestino;

  const marcarMensagem = useMutation({
    mutationFn: (mensagemId: string) =>
      avisosApi.marcarMensagemLida(avisoId as string, mensagemId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["aviso-mensagens", avisoId] }),
  });

  // Ao abrir a conversa, marca as mensagens recebidas como lidas.
  useEffect(() => {
    if (!mensagens) return;
    mensagens
      .filter((m) => !m.enviada_por_mim && !m.lida_em)
      .forEach((m) => marcarMensagem.mutate(m.id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mensagens?.length, avisoId]);

  return (
    <Modal
      open={!!avisoId}
      title={detalhe?.aviso.titulo ?? "Aviso"}
      onClose={onClose}
      size="lg"
    >
      {isLoading || !detalhe ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={PRIORIDADE_VARIANT[detalhe.aviso.prioridade] ?? "default"}>
              {PRIORIDADE_LABEL[detalhe.aviso.prioridade] ?? detalhe.aviso.prioridade}
            </Badge>
            {detalhe.aviso.permite_respostas && (
              <Badge variant="info">Aceita respostas</Badge>
            )}
            {detalhe.aviso.status === "arquivado" && <Badge variant="default">Arquivado</Badge>}
            <span className="text-xs text-gray-400">
              {new Date(detalhe.aviso.publicado_em).toLocaleString("pt-BR")}
            </span>
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400">
            Enviado por{" "}
            <span className="font-medium text-gray-700 dark:text-gray-200">
              {detalhe.aviso.autor_nome ?? "Usuário"}
            </span>
            {detalhe.aviso.autor_perfil ? ` (${detalhe.aviso.autor_perfil})` : ""}
          </div>

          <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
            {detalhe.aviso.mensagem}
          </p>

          {podeGerenciar && detalhe.estatisticas.total > 0 && (
            <div className="bg-gray-50 dark:bg-gray-800/40 rounded-xl p-3">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-gray-600 dark:text-gray-300">
                  Enviado para <strong>{detalhe.estatisticas.total}</strong> destinatário(s)
                </span>
                <span className="text-success-600 dark:text-success-400 flex items-center gap-1">
                  <CheckCheck className="h-4 w-4" /> {detalhe.estatisticas.lidos} visualizaram
                </span>
                <span className="text-gray-400">
                  {detalhe.estatisticas.nao_lidos} ainda não
                </span>
              </div>
              {detalhe.destinatarios.length > 0 && (
                <div className="max-h-48 overflow-y-auto mt-3 border border-gray-200 dark:border-gray-700 rounded-lg divide-y divide-gray-100 dark:divide-gray-800">
                  {detalhe.destinatarios.map((d) => (
                    <div
                      key={d.id}
                      className="flex items-center justify-between px-3 py-2 text-sm"
                    >
                      <span className="text-gray-700 dark:text-gray-200 truncate">
                        {d.usuario_nome ?? d.usuario_id}
                        {d.aluno_nome ? (
                          <span className="text-xs text-gray-400"> · {d.aluno_nome}</span>
                        ) : null}
                      </span>
                      <span className="flex items-center gap-2 flex-shrink-0">
                        {d.escalado_em && <Badge variant="danger">Escalado</Badge>}
                        {d.lido_em ? (
                          <Badge variant="success">
                            {`Lido ${new Date(d.lido_em).toLocaleString("pt-BR")}`}
                          </Badge>
                        ) : (
                          <Badge variant="warning">Não lido</Badge>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div>
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-primary-500" />
              Conversa ({detalhe.total_mensagens})
            </p>
            <div className="space-y-2 max-h-64 overflow-y-auto p-1">
              {(mensagens ?? []).length === 0 ? (
                <p className="text-sm text-gray-400">
                  {detalhe.aviso.permite_respostas
                    ? "Nenhuma resposta ainda."
                    : "Este aviso é somente informativo."}
                </p>
              ) : (
                (mensagens ?? []).map((m) => <MensagemBolha key={m.id} mensagem={m} />)
              )}
            </div>

            {detalhe.pode_responder && (
              <form
                className="mt-3 flex items-end gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!resposta.trim()) return;
                  if (souAutor && !destinoResposta) {
                    toast("warning", "Selecione para quem responder");
                    return;
                  }
                  responder.mutate();
                }}
              >
                <div className="flex-1">
                  {souAutor && detalhe.destinatarios.length > 0 && (
                    <select
                      className="w-full mb-1 px-2 py-1.5 text-xs bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg dark:text-gray-100"
                      value={destinoResposta}
                      onChange={(e) => setDestinoResposta(e.target.value)}
                      aria-label="Destinatário da resposta"
                    >
                      <option value="">Responder para...</option>
                      {detalhe.destinatarios.map((d) => (
                        <option key={d.id} value={d.usuario_id}>
                          {d.usuario_nome ?? d.usuario_id}
                        </option>
                      ))}
                    </select>
                  )}
                  <input
                    className="w-full px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
                    placeholder="Escreva uma resposta..."
                    value={resposta}
                    onChange={(e) => setResposta(e.target.value)}
                  />
                </div>
                <Button type="submit" loading={responder.isPending} disabled={!resposta.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              </form>
            )}
          </div>

          {podeGerenciar && detalhe.aviso.status === "publicado" && (
            <div className="flex justify-end pt-1">
              <Button
                variant="outline"
                onClick={() => arquivar.mutate()}
                loading={arquivar.isPending}
              >
                Arquivar aviso
              </Button>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

export function AvisosPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const isAdmin = user?.perfil === "admin";
  const podeEnviar = !!user?.perfil && SENDER_ROLES.includes(user.perfil);

  const [caixa, setCaixa] = useState<CaixaAviso>("recebidos");
  const [status, setStatus] = useState<StatusAviso | "">("");
  const [busca, setBusca] = useState("");
  const [buscaDebounced, setBuscaDebounced] = useState("");
  const [page, setPage] = useState(1);
  const [showComposer, setShowComposer] = useState(false);
  const [detalheId, setDetalheId] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setBuscaDebounced(busca.trim()), 350);
    return () => clearTimeout(timer);
  }, [busca]);

  useEffect(() => {
    const avisoParam = searchParams.get("aviso");
    if (avisoParam) {
      setDetalheId(avisoParam);
      const next = new URLSearchParams(searchParams);
      next.delete("aviso");
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["avisos", caixa, status, buscaDebounced, page],
    queryFn: () =>
      avisosApi.list({
        caixa,
        status: status || undefined,
        busca: buscaDebounced || undefined,
        page,
        size: 20,
      }),
  });

  const { data: publico } = useQuery({
    queryKey: ["avisos-publico"],
    queryFn: avisosApi.publico,
    enabled: podeEnviar && showComposer,
  });

  const avisos = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 1;

  const caixas: { value: CaixaAviso; label: string }[] = useMemo(() => {
    const base: { value: CaixaAviso; label: string }[] = [
      { value: "recebidos", label: "Recebidos" },
      { value: "enviados", label: "Enviados" },
    ];
    if (user?.perfil !== "responsavel") base.push({ value: "todos", label: "Todos" });
    if (isAdmin) base.push({ value: "global", label: "Global" });
    return base;
  }, [isAdmin, user?.perfil]);

  if (isError) {
    return (
      <div>
        <Breadcrumb items={[{ label: "Avisos" }]} />
        <Card>
          <ErrorState
            title="Erro ao carregar avisos"
            message="Não foi possível carregar os avisos."
            onRetry={() => queryClient.invalidateQueries({ queryKey: ["avisos"] })}
          />
        </Card>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={[{ label: "Avisos" }]} />
      <PageHeader
        title="Central de Avisos"
        description={`${total} aviso${total !== 1 ? "s" : ""} nesta caixa`}
        showNew={podeEnviar}
        onNew={() => setShowComposer(true)}
        newLabel="Novo Aviso"
      >
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            className="pl-9 pr-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100 w-full sm:w-56"
            placeholder="Buscar avisos..."
            value={busca}
            onChange={(e) => {
              setBusca(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <select
          className="px-3 py-2 text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-gray-100"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as StatusAviso | "");
            setPage(1);
          }}
          aria-label="Filtrar por status"
        >
          <option value="">Todos os status</option>
          <option value="publicado">Publicados</option>
          <option value="arquivado">Arquivados</option>
        </select>
      </PageHeader>

      <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1">
        {caixas.map((c) => (
          <button
            key={c.value}
            onClick={() => {
              setCaixa(c.value);
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
              caixa === c.value
                ? "bg-primary-500 text-white"
                : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      ) : avisos.length === 0 ? (
        <Card>
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <p className="text-lg">Nenhum aviso por aqui</p>
            <p className="text-sm mt-1">
              {caixa === "enviados"
                ? "Você ainda não enviou avisos."
                : "Quando chegarem avisos, eles aparecem aqui."}
            </p>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {avisos.map((aviso) => {
            const novo = caixa === "recebidos" && !aviso.lido_por_mim;
            return (
              <Card
                key={aviso.id}
                className={`hover:shadow-md transition-shadow cursor-pointer ${
                  novo ? "border-l-4 border-l-primary-500 epass-novo-pulse" : ""
                }`}
              >
                <button
                  className="w-full text-left"
                  onClick={() => setDetalheId(aviso.id)}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        {novo && <Badge variant="danger">Novo</Badge>}
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                          {aviso.titulo}
                        </h3>
                        <Badge variant={PRIORIDADE_VARIANT[aviso.prioridade] ?? "default"}>
                          {PRIORIDADE_LABEL[aviso.prioridade] ?? aviso.prioridade}
                        </Badge>
                        {aviso.permite_respostas && <Badge variant="info">Respostas</Badge>}
                        {aviso.status === "arquivado" && <Badge variant="default">Arquivado</Badge>}
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-300 mt-2 line-clamp-2">
                        {aviso.mensagem}
                      </p>
                      <p className="text-xs text-gray-400 mt-2 flex items-center gap-2 flex-wrap">
                        <span>
                          {aviso.sou_autor
                            ? "Enviado por você"
                            : `De ${aviso.autor_nome ?? "Sistema"}`}
                        </span>
                        <span>·</span>
                        <span>{new Date(aviso.publicado_em).toLocaleString("pt-BR")}</span>
                        {aviso.sou_autor && aviso.total_destinatarios > 0 && (
                          <>
                            <span>·</span>
                            <span className="flex items-center gap-1">
                              <CheckCheck className="h-3 w-3" />
                              {aviso.lidos}/{aviso.total_destinatarios} leram
                            </span>
                          </>
                        )}
                      </p>
                    </div>
                    {aviso.total_destinatarios > 0 && !aviso.sou_autor && (
                      <span className="text-xs text-gray-400 flex items-center gap-1 flex-shrink-0">
                        <Users className="h-3.5 w-3.5" />
                        {aviso.total_destinatarios}
                      </span>
                    )}
                  </div>
                </button>
              </Card>
            );
          })}
        </div>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-6">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Anterior
          </Button>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Página {page} de {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Próxima
          </Button>
        </div>
      )}

      <ComposerModal
        open={showComposer}
        onClose={() => setShowComposer(false)}
        publico={publico}
        onCreated={() => queryClient.invalidateQueries({ queryKey: ["avisos"] })}
      />
      <DetailModal avisoId={detalheId} onClose={() => setDetalheId(null)} />
      {!podeEnviar && (
        <p className="text-xs text-gray-400 mt-6 flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" />
          Responsáveis recebem avisos e podem responder quando o remetente permite.
        </p>
      )}
    </div>
  );
}
