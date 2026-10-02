import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Modal,
  RefreshControl,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { ThemedIcon } from "../../theme/ThemedIcon";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { ScreenHeader } from "../../components/ScreenHeader";
import { LoadingState } from "../../components/LoadingState";
import { EmptyState } from "../../components/EmptyState";
import { useToast } from "../../components/Toast";
import { getApiErrorMessage } from "../../api/errors";
import { getMyChildren } from "../../api/student.service";
import {
  STATUS_SOLICITACAO,
  TIPOS_DOCUMENTO,
  cancelarSolicitacao,
  criarSolicitacao,
  listarSolicitacoes,
  type SolicitacaoDocumento,
  type TipoDocumento,
} from "../../api/documentRequest.service";
import type { MyChildrenResponse } from "../../types/responsavel";

const STATUS_FILTRADOS = [
  "pendente",
  "em_analise",
  "concluida",
  "recusada",
] as const;

type FiltroAtivo = (typeof STATUS_FILTRADOS)[number] | "todos";

export function SolicitarDocumentosScreen() {
  useThemeVersion();
  const insets = useSafeAreaInsets();
  const toast = useToast();

  const [carregando, setCarregando] = useState(true);
  const [solicitacoes, setSolicitacoes] = useState<SolicitacaoDocumento[]>([]);
  const [filhos, setFilhos] = useState<MyChildrenResponse[]>([]);
  const [filtro, setFiltro] = useState<FiltroAtivo>("todos");
  const [atualizando, setAtualizando] = useState(false);

  const [formAberto, setFormAberto] = useState(false);
  const [tipo, setTipo] = useState<TipoDocumento>("boletim_bimestral");
  const [alunoId, setAlunoId] = useState<string>("");
  const [observacoes, setObservacoes] = useState("");
  const [enviando, setEnviando] = useState(false);

  const carregar = useCallback(
    async (opcoes?: { silencioso?: boolean }) => {
      if (opcoes?.silencioso) setAtualizando(true);
      else setCarregando(true);
      try {
        const [lista, meusFilhos] = await Promise.all([
          listarSolicitacoes(),
          getMyChildren(),
        ]);
        setSolicitacoes(lista);
        setFilhos(meusFilhos);
        if (meusFilhos.length > 0) {
          setAlunoId((atual) =>
            meusFilhos.some((f) => f.id === atual) ? atual : meusFilhos[0].id,
          );
        }
      } catch (err) {
        toast.error(getApiErrorMessage(err, "Não foi possível carregar"));
      } finally {
        setCarregando(false);
        setAtualizando(false);
      }
    },
    [toast],
  );

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const visiveis = useMemo(
    () =>
      filtro === "todos"
        ? solicitacoes
        : solicitacoes.filter((s) => s.status === filtro),
    [filtro, solicitacoes],
  );

  const contagem = useMemo(() => {
    const mapa: Record<string, number> = {};
    for (const s of solicitacoes) {
      if (s.status === "cancelada") continue;
      mapa[s.status] = (mapa[s.status] ?? 0) + 1;
    }
    return mapa;
  }, [solicitacoes]);

  const abrirForm = useCallback(() => {
    if (filhos.length === 0) {
      toast.warning("Você ainda não possui alunos vinculados.");
      return;
    }
    setFormAberto(true);
  }, [filhos.length, toast]);

  const enviar = useCallback(async () => {
    if (enviando) return;
    if (!alunoId) {
      toast.warning("Selecione o aluno da solicitação.");
      return;
    }
    if (tipo === "outro" && observacoes.trim().length < 5) {
      toast.warning("Descreva qual documento você precisa.");
      return;
    }

    setEnviando(true);
    try {
      const criada = await criarSolicitacao({
        aluno_id: alunoId,
        tipo,
        observacoes: observacoes.trim() || undefined,
      });
      setSolicitacoes((atual) => [criada, ...atual]);
      setFormAberto(false);
      setObservacoes("");
      toast.success("Solicitação enviada. A secretaria foi notificada.");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Não foi possível enviar"));
    } finally {
      setEnviando(false);
    }
  }, [alunoId, enviando, observacoes, toast, tipo]);

  // Cancelar é uma decisão destrutiva, então mantém o diálogo nativo
  // em vez de Toast (mesmo padrão de PedidoStatus/PersonalizarSemana).
  const cancelar = useCallback(
    (solicitacao: SolicitacaoDocumento) => {
      Alert.alert(
        "Cancelar solicitação",
        "A secretaria não vai mais analisar este pedido. Deseja cancelar?",
        [
          { text: "Voltar", style: "cancel" },
          {
            text: "Cancelar pedido",
            style: "destructive",
            onPress: () => {
              cancelarSolicitacao(solicitacao.id)
                .then((atualizada) => {
                  setSolicitacoes((atual) =>
                    atual.map((s) =>
                      s.id === atualizada.id ? atualizada : s,
                    ),
                  );
                  toast.success("Solicitação cancelada.");
                })
                .catch((err: unknown) => {
                  toast.error(
                    getApiErrorMessage(err, "Não foi possível cancelar"),
                  );
                });
            },
          },
        ],
      );
    },
    [toast],
  );

  if (carregando) {
    return (
      <View style={styles.container}>
        <ScreenHeader title="Solicitar documentos" />
        <LoadingState label="Carregando solicitações" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScreenHeader
        title="Solicitar documentos"
        subtitle="Acompanhe e peça documentos da escola"
      />

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + 100 },
        ]}
        refreshControl={
          <RefreshControl
            refreshing={atualizando}
            onRefresh={() => void carregar({ silencioso: true })}
            tintColor="#FF5B8F"
          />
        }
      >
        <View style={styles.resumo}>
          {STATUS_FILTRADOS.map((status) => {
            const info = STATUS_SOLICITACAO[status];
            const qtd = contagem[status] ?? 0;
            return (
              <View key={status} style={styles.resumoItem}>
                <ThemedIcon
                  name={info.icon as never}
                  size={20}
                  color={qtd > 0 ? info.cor : "#B0B0B0"}
                />
                <Text style={styles.resumoNumero}>{qtd}</Text>
                <Text style={styles.resumoLabel}>{info.label}</Text>
              </View>
            );
          })}
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filtros}
        >
          <FiltroChip
            ativo={filtro === "todos"}
            label="Todos"
            onPress={() => setFiltro("todos")}
          />
          {STATUS_FILTRADOS.map((status) => (
            <FiltroChip
              key={status}
              ativo={filtro === status}
              label={STATUS_SOLICITACAO[status].label}
              onPress={() => setFiltro(status)}
            />
          ))}
        </ScrollView>

        {visiveis.length === 0 ? (
          <EmptyState
            icon="document-text-outline"
            title="Nenhuma solicitação por aqui"
            description={
              filtro === "todos"
                ? "Toque em “Novo pedido” para solicitar um documento."
                : "Nenhum pedido com esse status no momento."
            }
          />
        ) : (
          visiveis.map((solicitacao) => (
            <SolicitacaoCard
              key={solicitacao.id}
              solicitacao={solicitacao}
              onCancelar={() => cancelar(solicitacao)}
            />
          ))
        )}
      </ScrollView>

      <View style={[styles.fabBar, { paddingBottom: insets.bottom + 12 }]}>
        <TouchableOpacity
          style={styles.fab}
          onPress={abrirForm}
          activeOpacity={0.85}
          accessibilityRole="button"
          accessibilityLabel="Novo pedido de documento"
        >
          <ThemedIcon name="add" size={22} color="#FFFFFF" />
          <Text style={styles.fabText}>Novo pedido</Text>
        </TouchableOpacity>
      </View>

      <Modal
        visible={formAberto}
        transparent
        animationType="fade"
        onRequestClose={() => setFormAberto(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Novo pedido</Text>
              <TouchableOpacity
                onPress={() => setFormAberto(false)}
                accessibilityRole="button"
                accessibilityLabel="Fechar"
              >
                <ThemedIcon name="close" size={24} color="#7A7A7A" />
              </TouchableOpacity>
            </View>

            {/*
              Os 9 tipos de documento somam mais altura que `maxHeight` do
              modal. Sem esta rolagem, o botão "Enviar solicitação" ficava
              fora da tela e o pedido não tinha como ser enviado.
            */}
            <ScrollView
              style={styles.modalBody}
              contentContainerStyle={styles.modalBodyContent}
              showsVerticalScrollIndicator={false}
              keyboardShouldPersistTaps="handled"
            >
              <Text style={styles.label}>Aluno</Text>
              <View style={styles.chips}>
                {filhos.map((filho) => (
                  <FiltroChip
                    key={filho.id}
                    ativo={alunoId === filho.id}
                    label={filho.nome}
                    onPress={() => setAlunoId(filho.id)}
                  />
                ))}
              </View>

              <Text style={styles.label}>Documento</Text>
              <View style={styles.tipos}>
                {TIPOS_DOCUMENTO.map((item) => {
                  const selecionado = tipo === item.id;
                  return (
                    <TouchableOpacity
                      key={item.id}
                      style={[
                        styles.tipoItem,
                        selecionado && styles.tipoItemAtivo,
                      ]}
                      onPress={() => setTipo(item.id)}
                      activeOpacity={0.8}
                      accessibilityRole="radio"
                      accessibilityState={{ selected: selecionado }}
                      accessibilityLabel={item.label}
                    >
                      <ThemedIcon
                        name={item.icon as never}
                        size={20}
                        color={selecionado ? "#FF5B8F" : "#7A7A7A"}
                      />
                      <Text
                        style={[
                          styles.tipoLabel,
                          selecionado && styles.tipoLabelAtivo,
                        ]}
                      >
                        {item.label}
                      </Text>
                      <Text style={styles.tipoDesc}>{item.descricao}</Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              <Text style={styles.label}>Observações (opcional)</Text>
              <TextInput
                style={styles.input}
                value={observacoes}
                onChangeText={setObservacoes}
                placeholder="Ex.: preciso do 2º bimestre"
                placeholderTextColor="#B0B0B0"
                multiline
                numberOfLines={3}
                accessibilityLabel="Observações"
              />
            </ScrollView>

            <TouchableOpacity
              style={[styles.primaryButton, enviando && styles.buttonDisabled]}
              onPress={enviar}
              disabled={enviando}
              activeOpacity={0.85}
              accessibilityRole="button"
              accessibilityLabel="Enviar solicitação"
            >
              {enviando ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <ThemedIcon name="send" size={18} color="#FFFFFF" />
              )}
              <Text style={styles.primaryButtonText}>Enviar solicitação</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

function FiltroChip({
  ativo,
  label,
  onPress,
}: {
  ativo: boolean;
  label: string;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={[styles.chip, ativo && styles.chipAtivo]}
      onPress={onPress}
      activeOpacity={0.8}
      accessibilityRole="button"
      accessibilityState={{ selected: ativo }}
      accessibilityLabel={label}
    >
      <Text style={[styles.chipLabel, ativo && styles.chipLabelAtivo]}>
        {label}
      </Text>
    </TouchableOpacity>
  );
}

function SolicitacaoCard({
  solicitacao,
  onCancelar,
}: {
  solicitacao: SolicitacaoDocumento;
  onCancelar: () => void;
}) {
  const status = STATUS_SOLICITACAO[solicitacao.status];
  const meta = TIPOS_DOCUMENTO.find((t) => t.id === solicitacao.tipo);
  const podeCancelar =
    solicitacao.status === "pendente" || solicitacao.status === "em_analise";

  return (
    <View style={styles.card}>
      <View style={styles.cardTopo}>
        <View style={styles.cardIcon}>
          <ThemedIcon
            name={(meta?.icon ?? "document-text-outline") as never}
            size={22}
            color="#FF5B8F"
          />
        </View>
        <View style={styles.cardInfo}>
          <Text style={styles.cardTitulo}>{meta?.label ?? solicitacao.tipo}</Text>
          <Text style={styles.cardSubtitulo}>
            {solicitacao.aluno_nome ?? "Aluno"}
          </Text>
        </View>
        <View style={styles.badgeStatus}>
          <ThemedIcon
            name={status.icon as never}
            size={14}
            color={status.cor}
          />
          <Text style={[styles.badgeStatusTexto, { color: status.cor }]}>
            {status.label}
          </Text>
        </View>
      </View>

      {solicitacao.observacoes ? (
        <Text style={styles.cardObs}>{solicitacao.observacoes}</Text>
      ) : null}

      {solicitacao.resposta ? (
        <View style={styles.respostaBox}>
          <Text style={styles.respostaTitulo}>Resposta da secretaria</Text>
          <Text style={styles.respostaTexto}>{solicitacao.resposta}</Text>
        </View>
      ) : null}

      {solicitacao.documento_url ? (
        <TouchableOpacity
          style={styles.downloadLink}
          onPress={() => Linking.openURL(solicitacao.documento_url as string)}
          accessibilityRole="link"
          accessibilityLabel="Abrir documento"
        >
          <ThemedIcon name="download-outline" size={18} color="#2D7FF9" />
          <Text style={styles.downloadText}>Abrir documento</Text>
        </TouchableOpacity>
      ) : null}

      <View style={styles.cardRodape}>
        <Text style={styles.cardData}>
          {new Date(solicitacao.created_at).toLocaleDateString("pt-BR")}
        </Text>
        {podeCancelar && (
          <TouchableOpacity
            onPress={onCancelar}
            accessibilityRole="button"
            accessibilityLabel="Cancelar solicitação"
          >
            <Text style={styles.cancelarLink}>Cancelar pedido</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = createThemedStyles({
  container: { flex: 1, backgroundColor: "#F5F5F7" },
  scroll: { flex: 1 },
  content: { paddingHorizontal: 24, paddingTop: 8, gap: 14 },

  resumo: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: "#FFFFFF",
    borderRadius: 24,
    padding: 16,
    borderWidth: 1,
    borderColor: "#E5E5E5",
  },
  resumoItem: { alignItems: "center", flex: 1, gap: 2 },
  resumoNumero: { fontSize: 18, fontWeight: "700", color: "#1F1F1F" },
  resumoLabel: { fontSize: 10, color: "#7A7A7A" },

  filtros: { gap: 8, paddingVertical: 4, paddingRight: 8 },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#E5E5E5",
  },
  chipAtivo: { backgroundColor: "#FF5B8F", borderColor: "#FF5B8F" },
  chipLabel: { fontSize: 13, fontWeight: "600", color: "#7A7A7A" },
  chipLabelAtivo: { color: "#FFFFFF" },

  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 24,
    padding: 16,
    borderWidth: 1,
    borderColor: "#E5E5E5",
    gap: 10,
  },
  cardTopo: { flexDirection: "row", alignItems: "center", gap: 12 },
  cardIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: "#FFEAF1",
    alignItems: "center",
    justifyContent: "center",
  },
  cardInfo: { flex: 1 },
  cardTitulo: { fontSize: 15, fontWeight: "700", color: "#1F1F1F" },
  cardSubtitulo: { fontSize: 13, color: "#7A7A7A", marginTop: 2 },
  badgeStatus: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: "#F0F0F3",
  },
  badgeStatusTexto: { fontSize: 11, fontWeight: "700" },
  cardObs: { fontSize: 13, color: "#7A7A7A", lineHeight: 18 },
  respostaBox: {
    backgroundColor: "#F0F6FF",
    borderRadius: 12,
    padding: 12,
    gap: 4,
  },
  respostaTitulo: { fontSize: 12, fontWeight: "700", color: "#2D7FF9" },
  respostaTexto: { fontSize: 13, color: "#1F1F1F", lineHeight: 18 },
  downloadLink: { flexDirection: "row", alignItems: "center", gap: 6 },
  downloadText: { fontSize: 13, fontWeight: "600", color: "#2D7FF9" },
  cardRodape: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: "#F0F0F3",
    paddingTop: 10,
  },
  cardData: { fontSize: 12, color: "#B0B0B0" },
  cancelarLink: { fontSize: 13, fontWeight: "600", color: "#E74C3C" },

  fabBar: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 24,
    paddingTop: 12,
    backgroundColor: "#F5F5F7",
  },
  fab: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#FF5B8F",
    borderRadius: 999,
    paddingVertical: 16,
  },
  fabText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" },

  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(15, 15, 20, 0.55)",
    justifyContent: "center",
    padding: 24,
  },
  modalCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 28,
    padding: 20,
    maxHeight: "88%",
  },
  // Só o corpo rola; título e botão de envio ficam sempre visíveis.
  modalBody: {
    flexShrink: 1,
  },
  modalBodyContent: {
    gap: 4,
    paddingBottom: 4,
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  modalTitle: { fontSize: 18, fontWeight: "700", color: "#1F1F1F" },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#7A7A7A",
    marginTop: 14,
    marginBottom: 8,
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  tipos: { gap: 8 },
  tipoItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 12,
    borderRadius: 16,
    backgroundColor: "#F5F5F7",
    borderWidth: 1,
    borderColor: "#E5E5E5",
  },
  tipoItemAtivo: { backgroundColor: "#FFEAF1", borderColor: "#FF5B8F" },
  tipoLabel: { fontSize: 14, fontWeight: "600", color: "#1F1F1F", flex: 1 },
  tipoLabelAtivo: { color: "#FF5B8F" },
  tipoDesc: { fontSize: 11, color: "#7A7A7A" },
  input: {
    backgroundColor: "#F0F0F3",
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 15,
    color: "#1F1F1F",
    borderWidth: 1,
    borderColor: "#E5E5E5",
    textAlignVertical: "top",
  },
  primaryButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#FF5B8F",
    borderRadius: 16,
    paddingVertical: 15,
    marginTop: 20,
  },
  buttonDisabled: { opacity: 0.5 },
  primaryButtonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" },
});
