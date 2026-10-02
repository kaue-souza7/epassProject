import { KeepAwake } from "../../components/KeepAwake";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  SafeAreaView,
  RefreshControl,
  ActivityIndicator,
  Modal,
  TextInput,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import {
  useFocusEffect,
  useNavigation,
  useRoute,
  type RouteProp,
} from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { ResponsavelStackParamList } from "../../types/navigation";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
import { useToast } from "../../components/Toast";
import {
  useAvisoActions,
  useAvisos,
  useNotificacaoActions,
  useNotificacoes,
  useNotificacoesNaoLidas,
} from "../../hooks/useCommunication";
import { useNotifications } from "../../contexts/NotificationsContext";
import { getApiErrorMessage } from "../../api/errors";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";
import {
  getAvisoDetalhe,
  getAvisoMensagens,
  marcarAvisoLido,
  marcarMensagemLida,
  responderAviso,
  type Aviso,
  type AvisoDetalhe,
  type AvisoMensagem,
  type Notificacao,
  type TipoNotificacao,
} from "../../api/communication.service";

type Aba = "avisos" | "notificacoes";

type AvisosRoute = RouteProp<
  { Avisos: { avisoId?: string } | undefined },
  "Avisos"
>;

const PRIORIDADE_CORES: Record<string, { bg: string; texto: string }> = {
  alta: { bg: "#FFE3E3", texto: "#C62828" },
  media: { bg: "#FFF3D6", texto: "#B26A00" },
  baixa: { bg: "#E3F2FD", texto: "#1565C0" },
};

const TIPO_NOTIFICACAO_ICONES: Record<TipoNotificacao, keyof typeof Ionicons.glyphMap> = {
  sistema: "settings-outline",
  cantina: "fast-food-outline",
  boletim: "document-text-outline",
  ocorrencia: "warning-outline",
  aviso: "megaphone-outline",
  agenda: "calendar-outline",
  financeiro: "wallet-outline",
  nota: "school-outline",
  frequencia: "checkbox-outline",
};

function formatarData(data: string): string {
  return new Date(data).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function AvisoCard({
  aviso,
  onAbrir,
}: {
  aviso: Aviso;
  onAbrir: (aviso: Aviso) => void;
}) {
  const cores = PRIORIDADE_CORES[aviso.prioridade] ?? PRIORIDADE_CORES.media;
  const naoLido = !aviso.lido_por_mim;

  return (
    <TouchableOpacity
      style={[styles.card, naoLido && styles.cardNaoLido]}
      activeOpacity={0.8}
      onPress={() => onAbrir(aviso)}
      accessibilityRole="button"
      accessibilityLabel={`Aviso: ${aviso.titulo}`}
    >
      <View style={styles.cardHeader}>
        {naoLido && <View style={styles.dotNaoLido} />}
        <Text style={styles.cardTitulo} numberOfLines={2}>
          {aviso.titulo}
        </Text>
        <View style={[styles.prioridadeBadge, { backgroundColor: cores.bg }]}>
          <Text style={[styles.prioridadeTexto, { color: cores.texto }]}>
            {aviso.prioridade.toUpperCase()}
          </Text>
        </View>
      </View>
      <Text style={styles.cardMensagem} numberOfLines={3}>
        {aviso.mensagem}
      </Text>
      <View style={styles.cardFooter}>
        <Text style={styles.cardAutor}>
          {aviso.autor_nome ? `De ${aviso.autor_nome}` : "Sistema"}
        </Text>
        <Text style={styles.cardData}>{formatarData(aviso.publicado_em)}</Text>
      </View>
      <View style={styles.cardTags}>
        {aviso.permite_respostas && (
          <View style={styles.tagResposta}>
            <ThemedIcon name="chatbubble-ellipses-outline" size={12} color="#FF5B8F" />
            <Text style={styles.tagRespostaTexto}>Aceita respostas</Text>
          </View>
        )}
        {aviso.sou_autor && aviso.total_destinatarios > 0 && (
          <Text style={styles.tagLeitura}>
            {aviso.lidos}/{aviso.total_destinatarios} leram
          </Text>
        )}
      </View>
    </TouchableOpacity>
  );
}

function NotificacaoCard({
  notificacao,
  onMarcarLida,
  onAbrir,
  marcando,
}: {
  notificacao: Notificacao;
  onMarcarLida: (id: string) => void;
  onAbrir: (n: Notificacao) => void;
  marcando: boolean;
}) {
  return (
    <TouchableOpacity
      style={[styles.card, !notificacao.lida && styles.cardNaoLido]}
      activeOpacity={0.8}
      onPress={() => onAbrir(notificacao)}
      accessibilityRole="button"
      accessibilityLabel={`Notificação: ${notificacao.titulo}`}
    >
      <View style={styles.cardHeader}>
        <ThemedIcon
          name={TIPO_NOTIFICACAO_ICONES[notificacao.tipo] ?? "notifications-outline"}
          size={20}
          color="#FF5B8F"
        />
        <Text style={styles.cardTitulo} numberOfLines={2}>
          {notificacao.titulo}
        </Text>
        {!notificacao.lida && <View style={styles.dotNaoLido} />}
      </View>
      <Text style={styles.cardMensagem}>{notificacao.mensagem}</Text>
      <View style={styles.notificacaoFooter}>
        <Text style={styles.cardData}>{formatarData(notificacao.created_at)}</Text>
        {!notificacao.lida && (
          <TouchableOpacity
            onPress={() => onMarcarLida(notificacao.id)}
            disabled={marcando}
            accessibilityLabel="Marcar notificação como lida"
            accessibilityRole="button"
          >
            <Text style={styles.botaoLidoTexto}>Marcar lida</Text>
          </TouchableOpacity>
        )}
      </View>
    </TouchableOpacity>
  );
}

function ConversaModal({
  aviso,
  onClose,
  onAtualizar,
}: {
  aviso: Aviso | null;
  onClose: () => void;
  onAtualizar: () => void;
}) {
  const [detalhe, setDetalhe] = useState<AvisoDetalhe | null>(null);
  const [mensagens, setMensagens] = useState<AvisoMensagem[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resposta, setResposta] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [destino, setDestino] = useState<string>("");
  const [seletorDestino, setSeletorDestino] = useState(false);

  const carregar = useCallback(async (signal?: AbortSignal) => {
    if (!aviso) return;
    setCarregando(true);
    setErro(null);
    try {
      const [d, m] = await Promise.all([
        getAvisoDetalhe(aviso.id, signal),
        getAvisoMensagens(aviso.id, signal),
      ]);
      setDetalhe(d);
      setMensagens(m);
      if (!d.aviso.sou_autor && !d.aviso.lido_por_mim) {
        await marcarAvisoLido(aviso.id, signal);
        setDetalhe({ ...d, aviso: { ...d.aviso, lido_por_mim: true } });
      }
      // marca mensagens recebidas como lidas
      const naoLidas = m.filter((msg) => !msg.enviada_por_mim && !msg.lida_em);
      if (naoLidas.length > 0) {
        await Promise.all(naoLidas.map((msg) => marcarMensagemLida(aviso.id, msg.id, signal)));
        setMensagens((prev) =>
          prev.map((msg) =>
            !msg.enviada_por_mim && !msg.lida_em
              ? { ...msg, lida_em: new Date().toISOString() }
              : msg,
          ),
        );
      }
    } catch (err) {
      if (!signal?.aborted) {
        setErro(getApiErrorMessage(err, "Erro ao carregar a conversa"));
      }
    } finally {
      setCarregando(false);
    }
  }, [aviso]);

  useEffect(() => {
    if (!aviso) {
      setDetalhe(null);
      setMensagens([]);
      setResposta("");
      setDestino("");
      return;
    }
    const controller = new AbortController();
    void carregar(controller.signal);
    return () => controller.abort();
  }, [aviso, carregar]);

  const enviar = useCallback(async () => {
    if (!aviso || !resposta.trim() || !detalhe?.pode_responder) return;
    if (detalhe.aviso.sou_autor && !destino) return;
    setEnviando(true);
    try {
      await responderAviso(
        aviso.id,
        resposta.trim(),
        detalhe.aviso.sou_autor ? destino : undefined,
      );
      setResposta("");
      await onAtualizar();
      await carregar();
    } catch (err) {
      setErro(getApiErrorMessage(err, "Erro ao enviar resposta"));
    } finally {
      setEnviando(false);
    }
  }, [aviso, resposta, detalhe, destino, onAtualizar, carregar]);

  const credito = useMemo(() => detalhe?.estatisticas, [detalhe]);

  return (
    <Modal visible={!!aviso} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={styles.modalContainer}
        >
          <View style={styles.modalHeader}>
            <TouchableOpacity onPress={onClose} accessibilityLabel="Fechar">
              <ThemedIcon name="close" size={26} color="#1F1F1F" />
            </TouchableOpacity>
            <Text style={styles.modalTitulo} numberOfLines={1}>
              {aviso?.titulo ?? "Aviso"}
            </Text>
            <View style={{ width: 26 }} />
          </View>

          {carregando && !detalhe ? (
            <LoadingState />
          ) : erro && !detalhe ? (
            <ErrorState message={erro} onRetry={() => carregar()} />
          ) : (
            <>
              <ScrollView style={styles.modalBody} contentContainerStyle={{ paddingBottom: 16 }}>
                <View style={styles.modalMeta}>
                  <Text style={styles.modalAutor}>
                    De {detalhe?.aviso.autor_nome ?? "Sistema"}
                    {detalhe?.aviso.autor_perfil ? ` · ${detalhe.aviso.autor_perfil}` : ""}
                  </Text>
                  <Text style={styles.modalData}>
                    {detalhe ? formatarData(detalhe.aviso.publicado_em) : ""}
                  </Text>
                </View>
                <Text style={styles.modalMensagem}>{detalhe?.aviso.mensagem}</Text>

                {detalhe?.aviso.sou_autor && credito && credito.total > 0 && (
                  <View style={styles.statsBox}>
                    <Text style={styles.statsTexto}>
                      Enviado para {credito.total} · {credito.lidos} visualizaram ·{" "}
                      {credito.nao_lidos} pendente(s)
                    </Text>
                    {detalhe.destinatarios.slice(0, 8).map((d) => (
                      <View key={d.id} style={styles.statsLinha}>
                        <Text style={styles.statsNome} numberOfLines={1}>
                          {d.usuario_nome ?? d.usuario_id}
                        </Text>
                        <Text
                          style={[
                            styles.statsStatus,
                            { color: d.lido_em ? "#4CAF50" : "#B0B0B0" },
                          ]}
                        >
                          {d.lido_em ? `lido ${formatarData(d.lido_em)}` : "não lido"}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}

                <Text style={styles.conversaTitulo}>
                  Conversa ({detalhe?.total_mensagens ?? mensagens.length})
                </Text>
                {mensagens.length === 0 ? (
                  <Text style={styles.conversaVazia}>
                    {detalhe?.aviso.permite_respostas
                      ? "Nenhuma resposta ainda."
                      : "Este aviso é somente informativo."}
                  </Text>
                ) : (
                  mensagens.map((m) => (
                    <View
                      key={m.id}
                      style={[
                        styles.bolha,
                        m.enviada_por_mim ? styles.bolhaMinha : styles.bolhaOutra,
                      ]}
                    >
                      {!m.enviada_por_mim && (
                        <Text style={styles.bolhaAutor}>{m.autor_nome ?? "Usuário"}</Text>
                      )}
                      <Text
                        style={[
                          styles.bolhaTexto,
                          m.enviada_por_mim && styles.bolhaTextoMinha,
                        ]}
                      >
                        {m.conteudo}
                      </Text>
                      <Text
                        style={[
                          styles.bolhaData,
                          m.enviada_por_mim && styles.bolhaDataMinha,
                        ]}
                      >
                        {formatarData(m.created_at)}
                        {m.enviada_por_mim && (m.lida_em ? " · lida" : " · enviada")}
                      </Text>
                    </View>
                  ))
                )}
                {detalhe?.aviso.status === "arquivado" && (
                  <Text style={styles.arquivadoAviso}>
                    Aviso arquivado — não aceita novas mensagens.
                  </Text>
                )}
              </ScrollView>

              {detalhe?.pode_responder && (
                <View style={styles.responderArea}>
                  {detalhe.aviso.sou_autor && (
                    <TouchableOpacity
                      style={styles.seletorDestino}
                      onPress={() => setSeletorDestino(true)}
                      accessibilityLabel="Escolher destinatário da resposta"
                    >
                      <Text style={styles.seletorDestinoTexto} numberOfLines={1}>
                        {destino
                          ? `Para: ${
                              detalhe.destinatarios.find((d) => d.usuario_id === destino)
                                ?.usuario_nome ?? destino
                            }`
                          : "Responder para..."}
                      </Text>
                      <ThemedIcon name="chevron-down" size={16} color="#888" />
                    </TouchableOpacity>
                  )}
                  <View style={styles.responderLinha}>
                    <TextInput
                      style={styles.responderInput}
                      placeholder="Escreva uma resposta..."
                      placeholderTextColor="#B0B0B0"
                      value={resposta}
                      onChangeText={setResposta}
                      multiline
                    />
                    <TouchableOpacity
                      style={[
                        styles.enviarBotao,
                        (!resposta.trim() || (detalhe.aviso.sou_autor && !destino)) &&
                          styles.enviarBotaoDisabled,
                      ]}
                      onPress={enviar}
                      disabled={enviando || !resposta.trim() || (detalhe.aviso.sou_autor && !destino)}
                      accessibilityLabel="Enviar resposta"
                      accessibilityRole="button"
                    >
                      {enviando ? (
                        <ActivityIndicator color="white" size="small" />
                      ) : (
                        <ThemedIcon name="send" size={18} color="white" />
                      )}
                    </TouchableOpacity>
                  </View>
                </View>
              )}
            </>
          )}
        </KeyboardAvoidingView>

        {/* Seletor de destinatário (autor respondendo) */}
        <Modal
          visible={seletorDestino}
          transparent
          animationType="fade"
          onRequestClose={() => setSeletorDestino(false)}
        >
          <TouchableOpacity
            style={styles.modalOverlay}
            activeOpacity={1}
            onPress={() => setSeletorDestino(false)}
          >
            <View style={styles.seletorLista}>
              <Text style={styles.seletorTitulo}>Escolha o destinatário</Text>
              {(detalhe?.destinatarios ?? []).map((d) => (
                <TouchableOpacity
                  key={d.id}
                  style={styles.seletorItem}
                  onPress={() => {
                    setDestino(d.usuario_id);
                    setSeletorDestino(false);
                  }}
                >
                  <Text style={styles.seletorItemTexto}>
                    {d.usuario_nome ?? d.usuario_id}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </TouchableOpacity>
        </Modal>
      </View>
    </Modal>
  );
}

export function AvisosScreen() {
  useThemeVersion();

  const route = useRoute<AvisosRoute>();
  const stackNavigation =
    useNavigation<NativeStackNavigationProp<ResponsavelStackParamList>>();
  const toast = useToast();
  const [aba, setAba] = useState<Aba>("avisos");
  const [avisoSelecionado, setAvisoSelecionado] = useState<Aviso | null>(null);
  const [avisoMarcando, setAvisoMarcando] = useState<string | null>(null);
  const [notificacaoMarcando, setNotificacaoMarcando] = useState<string | null>(null);

  const { versao, pushAtivo, motivoPush, solicitarPermissao } = useNotifications();

  const avisosQuery = useAvisos();
  const notificacoesQuery = useNotificacoes(false);
  const { total: totalNaoLidas, recarregar: recarregarNaoLidas } =
    useNotificacoesNaoLidas();
  const { marcarLido } = useAvisoActions();
  const { marcarLida, marcarTodasLidas } = useNotificacaoActions();

  const recarregarTudo = useCallback(async () => {
    await Promise.all([
      avisosQuery.refetch(),
      notificacoesQuery.refetch(),
      recarregarNaoLidas(),
    ]);
  }, [avisosQuery, notificacoesQuery, recarregarNaoLidas]);

  // Mantém a função de recarga em ref para o intervalo/foco não recriar.
  const recarregarRef = useRef(recarregarTudo);
  useEffect(() => {
    recarregarRef.current = recarregarTudo;
  }, [recarregarTudo]);

  // Push recebido → atualiza os dados
  useEffect(() => {
    if (versao > 0) void recarregarRef.current();
  }, [versao]);

  // Ao focar a tela, recarrega e mantém polling enquanto estiver visível.
  // É o fallback confiável quando o push remoto não está disponível (Expo Go).
  useFocusEffect(
    useCallback(() => {
      void recarregarRef.current();
      const timer = setInterval(() => void recarregarRef.current(), 30000);
      return () => clearInterval(timer);
    }, []),
  );

  // Sem avisos, mas com notificações não lidas: abre a aba correta uma vez,
  // para a ocorrência/aviso não ficar "escondido".
  const abaManualRef = useRef(false);
  const autoAbaRef = useRef(false);
  const avisosVisiveis = avisosQuery.data?.items ?? [];
  useEffect(() => {
    if (abaManualRef.current || autoAbaRef.current) return;
    if (!avisosQuery.data || !notificacoesQuery.data) return;
    if (totalNaoLidas > 0 && avisosVisiveis.length === 0) {
      autoAbaRef.current = true;
      setAba("notificacoes");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [totalNaoLidas, avisosQuery.data, notificacoesQuery.data]);

  const ativarPush = useCallback(async () => {
    const { ok, motivo } = await solicitarPermissao();
    if (ok) {
      toast.success("Notificações ativadas");
      return;
    }
    toast.warning(
      motivo ??
        "Não foi possível ativar as notificações. Os avisos continuam chegando na Central.",
    );
  }, [solicitarPermissao, toast]);

  // Deep link: abre o aviso vindo da notificação
  useEffect(() => {
    const avisoId = route.params?.avisoId;
    if (!avisoId) return;
    (async () => {
      try {
        const detalhe = await getAvisoDetalhe(avisoId);
        setAba("avisos");
        setAvisoSelecionado(detalhe.aviso);
      } catch {
        // aviso pode ter sido arquivado/removido
      }
    })();
  }, [route.params?.avisoId]);

  const handleMarcarAvisoLido = useCallback(
    async (id: string) => {
      setAvisoMarcando(id);
      const ok = await marcarLido(id);
      setAvisoMarcando(null);
      if (ok) await avisosQuery.refetch();
    },
    [marcarLido, avisosQuery],
  );

  const handleMarcarNotificacaoLida = useCallback(
    async (id: string) => {
      setNotificacaoMarcando(id);
      const ok = await marcarLida(id);
      setNotificacaoMarcando(null);
      if (ok) {
        await notificacoesQuery.refetch();
        await recarregarNaoLidas();
      }
    },
    [marcarLida, notificacoesQuery, recarregarNaoLidas],
  );

  const handleAbrirNotificacao = useCallback(
    async (n: Notificacao) => {
      if (!n.lida) await handleMarcarNotificacaoLida(n.id);
      const dados = n.dados as Record<string, unknown> | null;

      // Ocorrência → tela de detalhe própria
      const ocorrenciaId =
        (dados?.ocorrencia_id as string | undefined) ??
        (n.entidade_tipo === "ocorrencia" ? n.entidade_id ?? undefined : undefined);
      if (ocorrenciaId) {
        stackNavigation.navigate("OcorrenciaDetalhe", { ocorrenciaId });
        return;
      }

      const avisoId = (dados?.aviso_id as string | undefined) ?? n.entidade_id;
      if (n.entidade_tipo === "aviso" && avisoId) {
        try {
          const detalhe = await getAvisoDetalhe(avisoId);
          setAba("avisos");
          setAvisoSelecionado(detalhe.aviso);
        } catch {
          // ignora
        }
      }
    },
    [handleMarcarNotificacaoLida, stackNavigation],
  );

  const handleMarcarTodas = useCallback(async () => {
    const marcadas = await marcarTodasLidas();
    if (marcadas !== null) {
      await notificacoesQuery.refetch();
      await recarregarNaoLidas();
    }
  }, [marcarTodasLidas, notificacoesQuery, recarregarNaoLidas]);

  const avisos = avisosQuery.data?.items ?? [];
  const notificacoes = notificacoesQuery.data?.items ?? [];

  const carregando = aba === "avisos" ? avisosQuery.loading : notificacoesQuery.loading;
  const erro = aba === "avisos" ? avisosQuery.error : notificacoesQuery.error;

  return (
    <View style={styles.container}>
      {/* Evita a tela apagar durante a leitura. */}
      <KeepAwake />
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Avisos</Text>
          {totalNaoLidas > 0 && (
            <View style={styles.badgeHeader}>
              <Text style={styles.badgeHeaderTexto}>{totalNaoLidas}</Text>
            </View>
          )}
        </View>

        {!pushAtivo && (
          <TouchableOpacity
            style={styles.pushBanner}
            onPress={() => void ativarPush()}
            accessibilityLabel="Ativar notificações no dispositivo"
            accessibilityRole="button"
          >
            <ThemedIcon name="notifications-outline" size={18} color="#B26A00" />
            <Text style={styles.pushBannerTexto}>
              {motivoPush
                ? "Push indisponível — toque para detalhes"
                : "Ative as notificações para receber avisos na hora."}
            </Text>
          </TouchableOpacity>
        )}

        {aba === "avisos" && totalNaoLidas > 0 && (
          <TouchableOpacity
            style={styles.novidadeBanner}
            onPress={() => setAba("notificacoes")}
            accessibilityLabel={`Você tem ${totalNaoLidas} notificações não lidas. Ver agora`}
            accessibilityRole="button"
          >
            <View style={styles.novidadeIcone}>
              <ThemedIcon name="notifications" size={18} color="white" />
            </View>
            <Text style={styles.novidadeTexto}>
              Você tem {totalNaoLidas} notificaç{totalNaoLidas === 1 ? "ão" : "ões"} nova
              {totalNaoLidas === 1 ? "" : "s"} (avisos, ocorrências...)
            </Text>
            <Text style={styles.novidadeAcao}>Ver agora</Text>
          </TouchableOpacity>
        )}

        <View style={styles.tabs}>
          <TouchableOpacity
            style={[styles.tab, aba === "avisos" && styles.tabAtiva]}
            onPress={() => {
              abaManualRef.current = true;
              setAba("avisos");
            }}
            accessibilityRole="button"
            accessibilityLabel="Aba de avisos"
          >
            <Text style={[styles.tabTexto, aba === "avisos" && styles.tabTextoAtivo]}>
              Avisos
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tab, aba === "notificacoes" && styles.tabAtiva]}
            onPress={() => {
              abaManualRef.current = true;
              setAba("notificacoes");
            }}
            accessibilityRole="button"
            accessibilityLabel="Aba de notificações"
          >
            <Text
              style={[styles.tabTexto, aba === "notificacoes" && styles.tabTextoAtivo]}
            >
              Notificações{totalNaoLidas > 0 ? ` (${totalNaoLidas})` : ""}
            </Text>
          </TouchableOpacity>
        </View>

        {aba === "notificacoes" && notificacoes.some((n) => !n.lida) && (
          <TouchableOpacity
            style={styles.marcarTodas}
            onPress={handleMarcarTodas}
            accessibilityRole="button"
            accessibilityLabel="Marcar todas as notificações como lidas"
          >
            <Text style={styles.marcarTodasTexto}>Marcar todas como lidas</Text>
          </TouchableOpacity>
        )}

        {carregando && avisos.length === 0 && notificacoes.length === 0 ? (
          <LoadingState />
        ) : erro ? (
          <ErrorState message={erro} onRetry={recarregarTudo} />
        ) : aba === "avisos" ? (
          <FlatList
            data={avisos}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
              <AvisoCard aviso={item} onAbrir={setAvisoSelecionado} />
            )}
            contentContainerStyle={styles.lista}
            refreshControl={
              <RefreshControl
                refreshing={avisosQuery.loading}
                onRefresh={avisosQuery.refetch}
                tintColor="#FF5B8F"
              />
            }
            ListEmptyComponent={
              <View style={styles.vazio}>
                <ThemedIcon name="megaphone-outline" size={48} color="#C7C7C7" />
                <Text style={styles.vazioTexto}>Nenhum aviso no momento.</Text>
                {totalNaoLidas > 0 ? (
                  <Text style={styles.vazioDica}>
                    Você tem {totalNaoLidas} notificação(ões) na aba “Notificações”.
                  </Text>
                ) : null}
              </View>
            }
          />
        ) : (
          <FlatList
            data={notificacoes}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => (
              <NotificacaoCard
                notificacao={item}
                onMarcarLida={handleMarcarNotificacaoLida}
                onAbrir={handleAbrirNotificacao}
                marcando={notificacaoMarcando === item.id}
              />
            )}
            contentContainerStyle={styles.lista}
            refreshControl={
              <RefreshControl
                refreshing={notificacoesQuery.loading}
                onRefresh={recarregarTudo}
                tintColor="#FF5B8F"
              />
            }
            ListEmptyComponent={
              <View style={styles.vazio}>
                <ThemedIcon name="notifications-outline" size={48} color="#C7C7C7" />
                <Text style={styles.vazioTexto}>Nenhuma notificação no momento.</Text>
              </View>
            }
          />
        )}

        <ConversaModal
          aviso={avisoSelecionado}
          onClose={() => setAvisoSelecionado(null)}
          onAtualizar={recarregarTudo}
        />
      </SafeAreaView>
    </View>
  );
}

const styles = createThemedStyles({
  container: { flex: 1, backgroundColor: "#F5F5F7" },
  safeArea: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 8,
  },
  headerTitle: { fontSize: 24, fontWeight: "700", color: "#1F1F1F" },
  badgeHeader: {
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: "#FF5B8F",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
  },
  badgeHeaderTexto: { color: "white", fontSize: 12, fontWeight: "700" },
  pushBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginHorizontal: 24,
    marginBottom: 8,
    backgroundColor: "#FFF3D6",
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  pushBannerTexto: { flex: 1, color: "#B26A00", fontSize: 12, fontWeight: "600" },
  novidadeBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginHorizontal: 24,
    marginBottom: 8,
    backgroundColor: "#FF5B8F",
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  novidadeIcone: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: "rgba(255,255,255,0.22)",
    alignItems: "center",
    justifyContent: "center",
  },
  novidadeTexto: { flex: 1, color: "white", fontSize: 12, fontWeight: "600" },
  novidadeAcao: { color: "white", fontSize: 12, fontWeight: "800" },
  tabs: { flexDirection: "row", gap: 8, paddingHorizontal: 24, paddingBottom: 8 },
  tab: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 16,
    backgroundColor: "white",
    alignItems: "center",
  },
  tabAtiva: { backgroundColor: "#FF5B8F" },
  tabTexto: { fontSize: 14, fontWeight: "600", color: "#1F1F1F" },
  tabTextoAtivo: { color: "white" },
  marcarTodas: { alignSelf: "flex-end", marginHorizontal: 24, marginBottom: 4 },
  marcarTodasTexto: { color: "#FF5B8F", fontSize: 13, fontWeight: "600" },
  lista: { paddingHorizontal: 24, paddingBottom: 32 },
  card: { backgroundColor: "white", borderRadius: 20, padding: 16, marginBottom: 8 },
  cardNaoLido: { borderLeftWidth: 4, borderLeftColor: "#FF5B8F" },
  cardHeader: { flexDirection: "row", alignItems: "center", gap: 8 },
  dotNaoLido: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#FF5B8F" },
  cardTitulo: { flex: 1, fontSize: 15, fontWeight: "700", color: "#1F1F1F" },
  prioridadeBadge: { borderRadius: 8, paddingHorizontal: 8, paddingVertical: 2 },
  prioridadeTexto: { fontSize: 10, fontWeight: "700" },
  cardMensagem: { fontSize: 14, color: "#4A4A4A", marginTop: 6, lineHeight: 20 },
  cardFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 8,
  },
  cardAutor: { fontSize: 12, color: "#FF5B8F", fontWeight: "600" },
  cardData: { fontSize: 12, color: "#C7C7C7" },
  cardTags: { flexDirection: "row", alignItems: "center", gap: 10, marginTop: 6 },
  tagResposta: { flexDirection: "row", alignItems: "center", gap: 4 },
  tagRespostaTexto: { fontSize: 11, color: "#FF5B8F", fontWeight: "600" },
  tagLeitura: { fontSize: 11, color: "#7A7A7A" },
  notificacaoFooter: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 4,
  },
  vazio: { alignItems: "center", paddingTop: 80 },
  vazioTexto: {
    fontSize: 16,
    color: "#C7C7C7",
    fontWeight: "500",
    marginTop: 16,
  },
  vazioDica: {
    fontSize: 13,
    color: "#FF5B8F",
    fontWeight: "600",
    marginTop: 8,
    textAlign: "center",
  },
  botaoLidoTexto: { color: "#FF5B8F", fontSize: 13, fontWeight: "700" },
  lidoTexto: { color: "#4CAF50", fontSize: 13, fontWeight: "600" },

  // Modal de conversa
  modalOverlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", justifyContent: "flex-end" },
  modalContainer: {
    backgroundColor: "#F5F5F7",
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: "92%",
    minHeight: "60%",
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#E0E0E0",
  },
  modalTitulo: { flex: 1, textAlign: "center", fontSize: 17, fontWeight: "700", color: "#1F1F1F" },
  modalBody: { paddingHorizontal: 20 },
  modalMeta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 12,
  },
  modalAutor: { fontSize: 12, color: "#FF5B8F", fontWeight: "700" },
  modalData: { fontSize: 12, color: "#B0B0B0" },
  modalMensagem: { fontSize: 15, color: "#333", lineHeight: 22, marginTop: 10 },
  statsBox: {
    backgroundColor: "white",
    borderRadius: 14,
    padding: 12,
    marginTop: 14,
  },
  statsTexto: { fontSize: 12, color: "#4A4A4A", fontWeight: "600", marginBottom: 6 },
  statsLinha: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 4,
  },
  statsNome: { flex: 1, fontSize: 12, color: "#333", marginRight: 8 },
  statsStatus: { fontSize: 11, fontWeight: "600" },
  conversaTitulo: { fontSize: 13, fontWeight: "700", color: "#1F1F1F", marginTop: 18, marginBottom: 8 },
  conversaVazia: { fontSize: 13, color: "#B0B0B0" },
  bolha: { maxWidth: "85%", borderRadius: 16, paddingHorizontal: 12, paddingVertical: 8, marginBottom: 8 },
  bolhaMinha: { alignSelf: "flex-end", backgroundColor: "#FF5B8F", borderBottomRightRadius: 4 },
  bolhaOutra: { alignSelf: "flex-start", backgroundColor: "#FFFFFF", borderBottomLeftRadius: 4 },
  bolhaAutor: { fontSize: 11, fontWeight: "700", color: "#FF5B8F", marginBottom: 2 },
  bolhaTexto: { fontSize: 14, color: "#1F1F1F", lineHeight: 20 },
  bolhaTextoMinha: { color: "white" },
  bolhaData: { fontSize: 10, color: "#B0B0B0", marginTop: 4 },
  bolhaDataMinha: { color: "rgba(255,255,255,0.75)", textAlign: "right" },
  arquivadoAviso: { fontSize: 12, color: "#B26A00", marginTop: 12, fontWeight: "600" },
  responderArea: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: "#E0E0E0",
    padding: 12,
    backgroundColor: "white",
  },
  seletorDestino: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderWidth: 1,
    borderColor: "#E0E0E0",
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 6,
    marginBottom: 8,
  },
  seletorDestinoTexto: { fontSize: 12, color: "#4A4A4A", flex: 1, marginRight: 6 },
  responderLinha: { flexDirection: "row", alignItems: "flex-end", gap: 8 },
  responderInput: {
    flex: 1,
    maxHeight: 96,
    backgroundColor: "#F5F5F7",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    color: "#1F1F1F",
  },
  enviarBotao: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#FF5B8F",
    alignItems: "center",
    justifyContent: "center",
  },
  enviarBotaoDisabled: { opacity: 0.4 },
  seletorLista: {
    backgroundColor: "white",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingVertical: 16,
    paddingHorizontal: 20,
    maxHeight: "60%",
  },
  seletorTitulo: { fontSize: 15, fontWeight: "700", color: "#1F1F1F", marginBottom: 10 },
  seletorItem: { paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: "#EEE" },
  seletorItemTexto: { fontSize: 14, color: "#333" },
});
