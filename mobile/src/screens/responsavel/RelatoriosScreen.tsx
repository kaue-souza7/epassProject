import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  SafeAreaView,
  Share,
  Modal,
  Alert,
  Animated,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NavigationProp } from "@react-navigation/native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Paths, File } from "expo-file-system";
import * as Sharing from "expo-sharing";
import * as WebBrowser from "expo-web-browser";
import { Ionicons } from "@expo/vector-icons";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { ErrorState } from "../../components/ErrorState";
import { REPORT_ITEMS, generatePdf } from "../../api/report.service";
import type { ReportType, DocumentPdf } from "../../types/responsavel";
import type { ResponsavelStackParamList } from "../../types/navigation";

const FAVORITES_KEY = "@epass/favorite_reports";

const SECTION_LABELS: Record<string, string> = {
  academic: "Documentos Acadêmicos",
  financial: "Financeiro",
  performance: "Desempenho",
};

function SkeletonCard() {
  return (
    <View style={[styles.reportCard, styles.skeletonCard]}>
      <View style={[styles.skeletonIcon, styles.skeleton]} />
      <View style={styles.skeletonTextGroup}>
        <View style={[styles.skeletonLine, styles.skeleton, { width: "60%" }]} />
        <View style={[styles.skeletonLine, styles.skeleton, { width: "85%", marginTop: 6 }]} />
      </View>
    </View>
  );
}

const DISABLED_IDS: ReportType[] = ["comprovante_pagamento", "extrato_financeiro"];

export function RelatoriosScreen() {
  const navigation = useNavigation<NavigationProp<ResponsavelStackParamList>>();
  const { selectedChild } = useSelectedStudent();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [favorites, setFavorites] = useState<ReportType[]>([]);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<{
    item: (typeof REPORT_ITEMS)[number];
    pdf: DocumentPdf | null;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [generatingId, setGeneratingId] = useState<ReportType | null>(null);

  const loadFavorites = useCallback(async () => {
    try {
      const stored = await AsyncStorage.getItem(FAVORITES_KEY);
      if (stored) {
        setFavorites(JSON.parse(stored) as ReportType[]);
      }
    } catch {
      // ignore
    }
  }, []);

  const toggleFavorite = useCallback(
    async (id: ReportType) => {
      const next = favorites.includes(id)
        ? favorites.filter((f) => f !== id)
        : [...favorites, id];
      setFavorites(next);
      await AsyncStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
    },
    [favorites]
  );

  useEffect(() => {
    loadFavorites();
    const timer = setTimeout(() => {
      setLoading(false);
    }, 600);
    return () => clearTimeout(timer);
  }, [loadFavorites]);

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

  const academicItems = REPORT_ITEMS.filter((i) => i.section === "academic");
  const financialItems = REPORT_ITEMS.filter((i) => i.section === "financial");
  const performanceItems = REPORT_ITEMS.filter((i) => i.section === "performance");

  const favoriteItems = REPORT_ITEMS.filter(
    (i) => favorites.includes(i.id) && !DISABLED_IDS.includes(i.id)
  );

  const handleCardPress = async (item: (typeof REPORT_ITEMS)[number]) => {
    if (DISABLED_IDS.includes(item.id)) {
      return;
    }

    if (item.id === "boletim_anual") {
      navigation.navigate("BoletimAnual");
      return;
    }

    if (item.id === "boletim_bimestral") {
      navigation.navigate("Boletim");
      return;
    }

    setGeneratingId(item.id);
    setActionLoading(true);
    setError(null);
    try {
      const ids: {
        matricula_id?: string;
        aluno_id?: string;
        movimento_id?: string;
      } = {};
      if (selectedChild?.matricula_id) {
        ids.matricula_id = selectedChild.matricula_id;
      }
      if (selectedChild?.aluno_id) {
        ids.aluno_id = selectedChild.aluno_id;
      }
      const pdf = await generatePdf(item.id, ids);
      setSelectedDoc({ item, pdf });
      setModalVisible(true);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Erro ao gerar documento";
      setError(message);
    } finally {
      setActionLoading(false);
      setGeneratingId(null);
    }
  };

  const handleView = async (url: string) => {
    try {
      await WebBrowser.openBrowserAsync(url);
    } catch {
      Alert.alert("Erro", "Não foi possível abrir o documento");
    }
  };

  const handleShare = async (pdf: DocumentPdf) => {
    try {
      const file = await File.downloadFileAsync(pdf.url, Paths.cache);
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(file.uri, {
          mimeType: "application/pdf",
          dialogTitle: `Compartilhar ${pdf.nome_arquivo}`,
        });
      } else {
        await Share.share({
          message: pdf.url,
          title: pdf.nome_arquivo,
        });
      }
    } catch {
      await Share.share({
        message: pdf.url,
        title: pdf.nome_arquivo,
      });
    }
  };

  const handleDownload = async (pdf: DocumentPdf) => {
    try {
      const file = await File.downloadFileAsync(pdf.url, Paths.document);
      Alert.alert("Download concluído", `Arquivo salvo em:\n${file.uri}`);
    } catch {
      Alert.alert("Erro", "Não foi possível baixar o documento");
    }
  };

  const sections = [
    ...(favoriteItems.length > 0
      ? [{ key: "favorites", label: "Favoritos", items: favoriteItems }]
      : []),
    { key: "academic", label: "Documentos Acadêmicos", items: academicItems },
    { key: "financial", label: "Financeiro", items: financialItems },
    { key: "performance", label: "Desempenho", items: performanceItems },
  ];

  if (loading) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Relatórios</Text>
          </View>
          <ScrollView contentContainerStyle={styles.scrollContent}>
            {[1, 2, 3].map((i) => (
              <View key={i} style={{ marginBottom: 16 }}>
                <View style={[styles.skeleton, { width: "40%", height: 18, marginBottom: 12, borderRadius: 4 }]} />
                <SkeletonCard />
                <View style={{ height: 8 }} />
                <SkeletonCard />
              </View>
            ))}
          </ScrollView>
        </SafeAreaView>
      </View>
    );
  }

  if (error && !modalVisible) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Relatórios</Text>
          </View>
          <ErrorState message={error} onRetry={() => setError(null)} />
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Relatórios</Text>
        </View>

        {!selectedChild ? (
          <View style={styles.center}>
            <Ionicons name="people-outline" size={56} color="#D0D0D0" />
            <Text style={styles.emptyTitle}>Nenhum aluno selecionado</Text>
            <Text style={styles.emptySubtitle}>
              Selecione um aluno no menu superior para ver os relatórios.
            </Text>
          </View>
        ) : (
          <ScrollView
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            <View style={styles.yearSelector}>
              {years.map((y) => (
                <TouchableOpacity
                  key={y}
                  style={[
                    styles.yearChip,
                    y === selectedYear && styles.yearChipActive,
                  ]}
                  onPress={() => setSelectedYear(y)}
                  accessibilityLabel={`Ano ${y}`}
                  accessibilityRole="button"
                >
                  <Text
                    style={[
                      styles.yearChipText,
                      y === selectedYear && styles.yearChipTextActive,
                    ]}
                  >
                    {y}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {sections.map((section) => (
              <View key={section.key} style={styles.section}>
                <Text style={styles.sectionTitle}>{section.label}</Text>
                {section.items.map((item) => {
                  const isFav = favorites.includes(item.id);
                  const isGenerating = generatingId === item.id;
                  const isDisabled = DISABLED_IDS.includes(item.id);
                  return (
                    <TouchableOpacity
                      key={item.id}
                      style={[styles.reportCard, isDisabled && styles.reportCardDisabled]}
                      onPress={() => handleCardPress(item)}
                      activeOpacity={0.7}
                      disabled={actionLoading || isDisabled}
                      accessibilityLabel={`${item.title}. ${item.description}${isDisabled ? ". Indisponível" : ""}`}
                      accessibilityRole="button"
                    >
                      <View style={styles.reportCardLeft}>
                        <View style={[styles.reportIcon, isDisabled && styles.reportIconDisabled]}>
                          <Ionicons
                            name={item.icon as keyof typeof Ionicons.glyphMap}
                            size={22}
                            color={isDisabled ? "#C7C7C7" : "#FF5B8F"}
                          />
                        </View>
                        <View style={styles.reportInfo}>
                          <Text style={[styles.reportTitle, isDisabled && styles.reportTitleDisabled]}>
                            {item.title}
                          </Text>
                          <Text style={styles.reportDesc}>
                            {item.description}
                          </Text>
                        </View>
                      </View>
                      <View style={styles.reportCardRight}>
                        {isDisabled ? (
                          <View style={styles.comingSoonBadge}>
                            <Text style={styles.comingSoonText}>Em breve</Text>
                          </View>
                        ) : isGenerating ? (
                          <ActivityIndicator size="small" color="#FF5B8F" />
                        ) : (
                          <>
                            <TouchableOpacity
                              onPress={() => toggleFavorite(item.id)}
                              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                              accessibilityLabel={
                                isFav
                                  ? "Remover dos favoritos"
                                  : "Adicionar aos favoritos"
                              }
                              accessibilityRole="button"
                            >
                              <Ionicons
                                name={isFav ? "star" : "star-outline"}
                                size={20}
                                color={isFav ? "#FFB800" : "#C7C7C7"}
                              />
                            </TouchableOpacity>
                            <Ionicons
                              name="chevron-forward"
                              size={18}
                              color="#D0D0D0"
                              style={{ marginLeft: 8 }}
                            />
                          </>
                        )}
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </View>
            ))}

            <View style={{ height: 100 }} />
          </ScrollView>
        )}
      </SafeAreaView>

      <Modal
        visible={modalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            {selectedDoc && (
              <>
                <View style={styles.modalHeader}>
                  <View style={styles.modalIcon}>
                    <Ionicons
                      name={
                        selectedDoc.item.icon as keyof typeof Ionicons.glyphMap
                      }
                      size={28}
                      color="#FF5B8F"
                    />
                  </View>
                  <Text style={styles.modalTitle}>
                    {selectedDoc.item.title}
                  </Text>
                  <TouchableOpacity
                    onPress={() => setModalVisible(false)}
                    hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
                    accessibilityLabel="Fechar"
                    accessibilityRole="button"
                  >
                    <Ionicons name="close" size={24} color="#666" />
                  </TouchableOpacity>
                </View>

                <Text style={styles.modalSubtitle}>
                  {selectedChild?.aluno_nome} — {selectedYear}
                </Text>

                {actionLoading ? (
                  <View style={styles.modalLoading}>
                    <ActivityIndicator size="large" color="#FF5B8F" />
                    <Text style={styles.modalLoadingText}>
                      Gerando documento...
                    </Text>
                  </View>
                ) : selectedDoc.pdf ? (
                  <View style={styles.modalActions}>
                    <TouchableOpacity
                      style={styles.actionButton}
                      onPress={() => handleView(selectedDoc.pdf!.url)}
                      accessibilityLabel="Visualizar documento"
                      accessibilityRole="button"
                    >
                      <Ionicons name="eye" size={22} color="#FF5B8F" />
                      <Text style={styles.actionButtonText}>Visualizar</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.actionButton}
                      onPress={() => handleShare(selectedDoc.pdf!)}
                      accessibilityLabel="Compartilhar documento"
                      accessibilityRole="button"
                    >
                      <Ionicons name="share-outline" size={22} color="#FF5B8F" />
                      <Text style={styles.actionButtonText}>Compartilhar</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.actionButton}
                      onPress={() => handleDownload(selectedDoc.pdf!)}
                      accessibilityLabel="Baixar documento"
                      accessibilityRole="button"
                    >
                      <Ionicons name="download-outline" size={22} color="#FF5B8F" />
                      <Text style={styles.actionButtonText}>Download</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.actionButton}
                      onPress={() => {
                        toggleFavorite(selectedDoc!.item.id);
                      }}
                      accessibilityLabel={
                        favorites.includes(selectedDoc!.item.id)
                          ? "Remover dos favoritos"
                          : "Adicionar aos favoritos"
                      }
                      accessibilityRole="button"
                    >
                      <Ionicons
                        name={
                          favorites.includes(selectedDoc!.item.id)
                            ? "star"
                            : "star-outline"
                        }
                        size={22}
                        color="#FFB800"
                      />
                      <Text style={[styles.actionButtonText, { color: "#FFB800" }]}>
                        {favorites.includes(selectedDoc!.item.id)
                          ? "Favoritado"
                          : "Favoritar"}
                      </Text>
                    </TouchableOpacity>
                  </View>
                ) : error ? (
                  <View style={styles.modalError}>
                    <Text style={styles.modalErrorText}>{error}</Text>
                    <TouchableOpacity
                      style={styles.modalRetryButton}
                      onPress={() => {
                        setError(null);
                        handleCardPress(selectedDoc!.item);
                      }}
                    >
                      <Text style={styles.modalRetryText}>Tentar novamente</Text>
                    </TouchableOpacity>
                  </View>
                ) : null}

                <TouchableOpacity
                  style={styles.modalCloseButton}
                  onPress={() => setModalVisible(false)}
                  accessibilityLabel="Fechar"
                  accessibilityRole="button"
                >
                  <Text style={styles.modalCloseText}>Fechar</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F7",
  },
  safeArea: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 8,
  },
  headerTitle: {
    fontSize: 40,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 32,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1F1F1F",
    marginTop: 16,
    textAlign: "center",
  },
  emptySubtitle: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    marginTop: 8,
    lineHeight: 20,
  },
  yearSelector: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 24,
    flexWrap: "wrap",
  },
  yearChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#FFF",
  },
  yearChipActive: {
    backgroundColor: "#FF5B8F",
  },
  yearChipText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#666",
  },
  yearChipTextActive: {
    color: "#FFF",
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 12,
  },
  reportCard: {
    backgroundColor: "#FFF",
    borderRadius: 20,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  reportCardLeft: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
  },
  reportIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: "#FFF0F3",
    justifyContent: "center",
    alignItems: "center",
  },
  reportInfo: {
    marginLeft: 14,
    flex: 1,
  },
  reportTitle: {
    fontSize: 15,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  reportDesc: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  reportCardRight: {
    flexDirection: "row",
    alignItems: "center",
  },
  reportCardDisabled: {
    opacity: 0.6,
  },
  reportIconDisabled: {
    backgroundColor: "#F0F0F0",
  },
  reportTitleDisabled: {
    color: "#B0B0B0",
  },
  comingSoonBadge: {
    backgroundColor: "#F0F0F0",
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  comingSoonText: {
    fontSize: 11,
    fontWeight: "600",
    color: "#999",
  },
  skeletonCard: {
    opacity: 0.6,
  },
  skeleton: {
    backgroundColor: "#E5E5E5",
    borderRadius: 6,
  },
  skeletonIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
  },
  skeletonTextGroup: {
    marginLeft: 14,
    flex: 1,
  },
  skeletonLine: {
    height: 14,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "flex-end",
  },
  modalContent: {
    backgroundColor: "#FFF",
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    padding: 24,
    paddingBottom: 40,
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  modalIcon: {
    width: 48,
    height: 48,
    borderRadius: 16,
    backgroundColor: "#FFF0F3",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1F1F1F",
    flex: 1,
  },
  modalSubtitle: {
    fontSize: 14,
    color: "#888",
    marginBottom: 24,
    marginLeft: 62,
  },
  modalLoading: {
    alignItems: "center",
    paddingVertical: 32,
  },
  modalLoadingText: {
    fontSize: 14,
    color: "#888",
    marginTop: 12,
  },
  modalActions: {
    gap: 12,
    marginBottom: 24,
  },
  actionButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#F8F8FA",
    borderRadius: 16,
    padding: 16,
    gap: 14,
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  modalError: {
    alignItems: "center",
    paddingVertical: 24,
  },
  modalErrorText: {
    fontSize: 14,
    color: "#F44336",
    textAlign: "center",
    marginBottom: 16,
  },
  modalRetryButton: {
    borderWidth: 2,
    borderColor: "#FF5B8F",
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 10,
  },
  modalRetryText: {
    color: "#FF5B8F",
    fontSize: 14,
    fontWeight: "700",
  },
  modalCloseButton: {
    alignItems: "center",
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: "#F0F0F0",
  },
  modalCloseText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#888",
  },
});
