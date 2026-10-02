import { KeepAwake } from "../../components/KeepAwake";
import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ScrollView,
} from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { LoadingState } from "../../components/LoadingState";
import { ErrorState } from "../../components/ErrorState";
import { getApiErrorMessage } from "../../api/errors";
import {
  getOcorrencia,
  type OcorrenciaDetalhe,
  type SeveridadeOcorrencia,
  type StatusOcorrencia,
  type TipoOcorrencia,
} from "../../api/communication.service";
import type { ResponsavelStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type Props = NativeStackScreenProps<ResponsavelStackParamList, "OcorrenciaDetalhe">;

const STATUS_LABEL: Record<StatusOcorrencia, string> = {
  aberta: "Aberta",
  em_andamento: "Em andamento",
  resolvida: "Resolvida",
  arquivada: "Arquivada",
};

const STATUS_CORES: Record<StatusOcorrencia, { bg: string; texto: string }> = {
  aberta: { bg: "#E3F2FD", texto: "#1565C0" },
  em_andamento: { bg: "#FFF3D6", texto: "#B26A00" },
  resolvida: { bg: "#E8F5E9", texto: "#2E7D32" },
  arquivada: { bg: "#EEEEEE", texto: "#616161" },
};

const SEVERIDADE_LABEL: Record<SeveridadeOcorrencia, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};

const SEVERIDADE_CORES: Record<SeveridadeOcorrencia, { bg: string; texto: string }> = {
  baixa: { bg: "#E3F2FD", texto: "#1565C0" },
  media: { bg: "#FFF3D6", texto: "#B26A00" },
  alta: { bg: "#FFE3E3", texto: "#C62828" },
};

const TIPO_LABEL: Record<TipoOcorrencia, string> = {
  comportamento: "Comportamento",
  saude: "Saúde",
  academico: "Acadêmico",
  outro: "Outro",
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

export function OcorrenciaDetalheScreen({ route, navigation }: Props) {
  useThemeVersion();

  const { ocorrenciaId } = route.params;
  const [detalhe, setDetalhe] = useState<OcorrenciaDetalhe | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(
    async (signal?: AbortSignal) => {
      setCarregando(true);
      setErro(null);
      try {
        const data = await getOcorrencia(ocorrenciaId, signal);
        setDetalhe(data);
      } catch (err) {
        if (!signal?.aborted) {
          setErro(getApiErrorMessage(err, "Erro ao carregar a ocorrência"));
        }
      } finally {
        setCarregando(false);
      }
    },
    [ocorrenciaId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void carregar(controller.signal);
    return () => controller.abort();
  }, [carregar]);

  const ocorrencia = detalhe?.ocorrencia;

  return (
    <View style={styles.container}>
      {/* Evita a tela apagar durante a leitura. */}
      <KeepAwake />
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            accessibilityLabel="Voltar"
            accessibilityRole="button"
          >
            <ThemedIcon name="arrow-back" size={24} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Ocorrência</Text>
          <View style={{ width: 24 }} />
        </View>

        {carregando ? (
          <LoadingState />
        ) : erro || !ocorrencia ? (
          <ErrorState message={erro ?? "Ocorrência não encontrada"} onRetry={() => carregar()} />
        ) : (
          <ScrollView contentContainerStyle={styles.conteudo}>
            <Text style={styles.titulo}>{ocorrencia.titulo}</Text>

            <View style={styles.tags}>
              <View
                style={[
                  styles.tag,
                  { backgroundColor: STATUS_CORES[ocorrencia.status].bg },
                ]}
              >
                <Text
                  style={[styles.tagTexto, { color: STATUS_CORES[ocorrencia.status].texto }]}
                >
                  {STATUS_LABEL[ocorrencia.status]}
                </Text>
              </View>
              <View
                style={[
                  styles.tag,
                  { backgroundColor: SEVERIDADE_CORES[ocorrencia.severidade].bg },
                ]}
              >
                <Text
                  style={[
                    styles.tagTexto,
                    { color: SEVERIDADE_CORES[ocorrencia.severidade].texto },
                  ]}
                >
                  {SEVERIDADE_LABEL[ocorrencia.severidade]}
                </Text>
              </View>
              <View style={[styles.tag, { backgroundColor: "#F0F0F0" }]}>
                <Text style={[styles.tagTexto, { color: "#616161" }]}>
                  {TIPO_LABEL[ocorrencia.tipo]}
                </Text>
              </View>
            </View>

            <View style={styles.infoBox}>
              {ocorrencia.aluno_nome && (
                <View style={styles.infoLinha}>
                  <ThemedIcon name="person-outline" size={16} color="#FF5B8F" />
                  <Text style={styles.infoTexto}>
                    Aluno: <Text style={styles.infoForte}>{ocorrencia.aluno_nome}</Text>
                  </Text>
                </View>
              )}
              {ocorrencia.turma_codigo && (
                <View style={styles.infoLinha}>
                  <ThemedIcon name="school-outline" size={16} color="#FF5B8F" />
                  <Text style={styles.infoTexto}>
                    Turma: <Text style={styles.infoForte}>{ocorrencia.turma_codigo}</Text>
                  </Text>
                </View>
              )}
              <View style={styles.infoLinha}>
                <ThemedIcon name="time-outline" size={16} color="#FF5B8F" />
                <Text style={styles.infoTexto}>{formatarData(ocorrencia.created_at)}</Text>
              </View>
            </View>

            <Text style={styles.secaoTitulo}>Descrição</Text>
            <Text style={styles.descricao}>{ocorrencia.descricao}</Text>

            {(detalhe?.historico?.length ?? 0) > 0 && (
              <>
                <Text style={styles.secaoTitulo}>Histórico</Text>
                <View style={styles.historico}>
                  {detalhe!.historico.map((h) => (
                    <View key={h.id} style={styles.historicoItem}>
                      <Text style={styles.historicoAcao}>{h.acao}</Text>
                      <Text style={styles.historicoData}>{formatarData(h.created_at)}</Text>
                    </View>
                  ))}
                </View>
              </>
            )}
          </ScrollView>
        )}
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
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  headerTitle: { fontSize: 18, fontWeight: "700", color: "#1F1F1F" },
  conteudo: { paddingHorizontal: 20, paddingBottom: 40 },
  titulo: { fontSize: 22, fontWeight: "700", color: "#1F1F1F", marginBottom: 12 },
  tags: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 16 },
  tag: { borderRadius: 10, paddingHorizontal: 10, paddingVertical: 4 },
  tagTexto: { fontSize: 12, fontWeight: "700" },
  infoBox: { backgroundColor: "white", borderRadius: 16, padding: 14, gap: 8 },
  infoLinha: { flexDirection: "row", alignItems: "center", gap: 8 },
  infoTexto: { fontSize: 13, color: "#4A4A4A" },
  infoForte: { fontWeight: "700", color: "#1F1F1F" },
  secaoTitulo: {
    fontSize: 13,
    fontWeight: "700",
    color: "#7A7A7A",
    textTransform: "uppercase",
    marginTop: 20,
    marginBottom: 8,
  },
  descricao: { fontSize: 15, lineHeight: 22, color: "#333" },
  historico: { backgroundColor: "white", borderRadius: 16, padding: 14, gap: 10 },
  historicoItem: { borderLeftWidth: 3, borderLeftColor: "#FF5B8F", paddingLeft: 10 },
  historicoAcao: { fontSize: 13, color: "#333", fontWeight: "600" },
  historicoData: { fontSize: 11, color: "#B0B0B0", marginTop: 2 },
});
