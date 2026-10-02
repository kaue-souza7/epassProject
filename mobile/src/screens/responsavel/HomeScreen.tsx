import { useState, useCallback, useEffect } from "react";
import { useNavigation, useFocusEffect } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  SafeAreaView,
  RefreshControl,
  Platform,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { useEvents } from "../../hooks/useAgenda";
import { useWallet } from "../../hooks/useWallet";
import { useAttendance } from "../../hooks/useAttendance";
import { useDashboard } from "../../hooks/useDashboard";
import { ErrorState } from "../../components/ErrorState";
import type { ResponsavelStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "HomeTabs">;

function daysUntil(dateStr: string): number {
  const now = new Date();
  const target = new Date(dateStr);
  const diff = target.getTime() - now.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

export function HomeScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const { selectedChild, selectChild } = useSelectedStudent();
  const { events, loading: loadingEvents, refetch: refetchEvents } = useEvents({ size: 5 });
  const { saldo, loading: loadingWallet, refetch: refetchWallet } = useWallet();
  const { frequency, loading: loadingFrequency, refetch: refetchFrequency } = useAttendance();
  const { data: dashboardData, refetch: refetchDashboard } = useDashboard();
  const insets = useSafeAreaInsets();
  const [refreshing, setRefreshing] = useState(false);

  useFocusEffect(
    useCallback(() => {
      refetchWallet();
      refetchFrequency();
      refetchEvents();
      refetchDashboard();
    }, [refetchWallet, refetchFrequency, refetchEvents, refetchDashboard])
  );

  useEffect(() => {
    if (!dashboardData || !selectedChild) return;
    const updated = dashboardData.filhos?.find(
      (f) => f.aluno_id === selectedChild.aluno_id
    );
    if (!updated) return;
    if (
      updated.media_geral !== selectedChild.media_geral ||
      updated.frequencia_media !== selectedChild.frequencia_media ||
      updated.situacao !== selectedChild.situacao
    ) {
      selectChild(updated);
    }
  }, [dashboardData, selectedChild, selectChild]);

  // Altura ocupada pelo StudentSelector (~52px: paddingVertical 16 + avatar 32)
  // + selectorOuter marginBottom (8px) + TabBar (~50px: paddingVertical 12 + ícone 20 + label 12)
  // Valores baseados nos estilos de ResponsavelTabNavigator.tsx
  const TAB_BAR_OVERLAY_HEIGHT = 110;
  const scrollBottomPadding = TAB_BAR_OVERLAY_HEIGHT + insets.bottom + 16;

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([refetchEvents(), refetchWallet(), refetchFrequency(), refetchDashboard()]);
    setRefreshing(false);
  }, [refetchEvents, refetchWallet, refetchFrequency]);

  const isLoading = loadingEvents && !events;

  if (isLoading) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#FF5B8F" />
            <Text style={styles.statusText}>Carregando...</Text>
          </View>
        </SafeAreaView>
      </View>
    );
  }

  if (!selectedChild) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.center}>
            <Text style={styles.errorText}>Nenhum aluno selecionado</Text>
            <TouchableOpacity
              style={styles.retryButton}
              onPress={() => navigation.getParent()?.navigate("SelectStudent")}
            >
              <Text style={styles.retryText}>Selecionar aluno</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </View>
    );
  }

  const eventList = events?.items ?? [];
  const displayEvents = eventList.slice(0, 5).map((e) => ({
    id: e.id,
    title: e.titulo,
    category: "Evento",
    days_remaining: daysUntil(e.data_inicio),
  }));

  const mediaGeral = selectedChild.media_geral;
  const freqPct = frequency?.frequencia_media ?? selectedChild.frequencia_media;
  const progressColor =
    freqPct != null
      ? freqPct >= 85
         ? "#4CAF50"
         : freqPct >= 70
           ? "#FF9800"
           : "#F44336"
       : "#C7C7C7";

  const situacaoHoje = frequency?.situacao_hoje;
  const hojeLabel =
    situacaoHoje === "presente"
       ? "Compareceu à aula hoje"
       : situacaoHoje === "falta"
         ? "Falta registrada hoje"
         : situacaoHoje === "falta_justificada"
           ? "Falta justificada hoje"
           : null;

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          contentContainerStyle={[styles.scrollContent, { paddingBottom: scrollBottomPadding }]}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              tintColor="#FF5B8F"
            />
          }
        >
          <Text style={styles.headerTitle}>Resumo</Text>

          <LinearGradient
            colors={["#F84F8D", "#FF8664"]}
            start={{ x: 0, y: 0.5 }}
            end={{ x: 1, y: 0.5 }}
            style={styles.heroCard}
          >
            <View style={styles.decorGlow1} />
            <View style={styles.decorGlow2} />
            <View style={styles.decorGlow3} />
            <View style={styles.decorDot1} />
            <View style={styles.decorDot2} />
            <View style={styles.decorDot3} />

            <LinearGradient
              colors={["rgba(255,255,255,0.22)", "rgba(255,255,255,0.06)"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.atenaGlass}
            >
              <Image
                source={require("../../../assets/images/atena/atena-logo.png")}
                style={styles.atenaImage}
              />
              <View style={styles.atenaTextGroup}>
                <Text style={styles.atenaGreeting}>
                  Olá, {selectedChild.aluno_nome.split(" ")[0]}! ✨
                </Text>
                <Text style={styles.atenaSubtitle}>
                  Pergunte o que quiser para a{" "}
                  <Text style={styles.atenaHighlight}>Atena</Text>
                </Text>
              </View>
            </LinearGradient>

            <TouchableOpacity
              style={styles.atenaButton}
              onPress={() => navigation.navigate("AtenaChat")}
              accessibilityLabel="Falar com Atena"
              accessibilityRole="button"
            >
              <Text style={styles.atenaButtonText}>Falar com Atena</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.liberarButton}
              onPress={() => navigation.navigate("LiberarAluno")}
              accessibilityLabel="Liberar aluno"
              accessibilityRole="button"
            >
              <ThemedIcon name="walk-outline" size={18} color="rgba(255,255,255,0.85)" />
              <Text style={styles.liberarButtonText}>Liberar Aluno</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.carteirinhaLink}
              onPress={() => navigation.navigate("CarteirinhaDigital")}
              accessibilityLabel="Carteirinha Digital"
              accessibilityRole="button"
            >
              <ThemedIcon name="wallet-outline" size={15} color="rgba(255,255,255,0.5)" />
              <Text style={styles.carteirinhaLinkText}>Carteirinha Digital</Text>
            </TouchableOpacity>
          </LinearGradient>

          {mediaGeral != null && (
            <View style={styles.statsRow}>
              <View style={[styles.statCard, { backgroundColor: "#FFF0F3" }]}>
                <Text style={styles.statLabel}>Média Geral</Text>
                <Text
                  style={[
                    styles.statValue,
                    { color: mediaGeral >= 6 ? "#4CAF50" : "#F44336" },
                  ]}
                >
                  {mediaGeral.toFixed(1)}
                </Text>
              </View>
              <View style={[styles.statCard, { backgroundColor: "#E8F5E9" }]}>
                <Text style={styles.statLabel}>Frequência</Text>
                {loadingFrequency ? (
                  <ActivityIndicator size="small" color="#4CAF50" />
                ) : (
                  <Text style={[styles.statValue, { color: progressColor }]}>
                    {freqPct != null ? `${freqPct.toFixed(0)}%` : "—"}
                  </Text>
                )}
              </View>
            </View>
          )}

          {frequency && (
            <View style={styles.freqDetailCard}>
              {hojeLabel && (
                <View style={styles.hojeRow}>
                  <ThemedIcon
                    name={
                      situacaoHoje === "presente"
                        ? "checkmark-circle"
                        : situacaoHoje === "falta_justificada"
                          ? "time"
                          : "alert-circle"
                    }
                    size={20}
                    color={
                      situacaoHoje === "presente"
                        ? "#4CAF50"
                        : situacaoHoje === "falta_justificada"
                          ? "#FF9800"
                          : "#F44336"
                    }
                  />
                  <Text
                    style={[
                      styles.hojeText,
                      {
                        color:
                          situacaoHoje === "presente"
                            ? "#4CAF50"
                            : situacaoHoje === "falta_justificada"
                              ? "#FF9800"
                              : "#F44336",
                      },
                    ]}
                  >
                    {hojeLabel}
                  </Text>
                </View>
              )}
              {freqPct != null && (
                <View style={styles.progressContainer}>
                  <View style={styles.progressBg}>
                    <View
                      style={[
                        styles.progressFill,
                        {
                          width: `${Math.min(freqPct, 100)}%`,
                          backgroundColor: progressColor,
                        },
                      ]}
                    />
                  </View>
                </View>
              )}
              {frequency.total_aulas > 0 && (
                <View style={styles.freqBreakdown}>
                  <Text style={styles.freqBreakdownItem}>
                    <Text style={{ color: "#4CAF50", fontWeight: "700" }}>
                      {frequency.presencas}
                    </Text>{" "}
                    presenças
                  </Text>
                  <Text style={styles.freqBreakdownItem}>
                    <Text style={{ color: "#F44336", fontWeight: "700" }}>
                      {frequency.faltas}
                    </Text>{" "}
                    faltas
                  </Text>
                  {frequency.faltas_justificadas > 0 && (
                    <Text style={styles.freqBreakdownItem}>
                      <Text style={{ color: "#FF9800", fontWeight: "700" }}>
                        {frequency.faltas_justificadas}
                      </Text>{" "}
                      justificadas
                    </Text>
                  )}
                </View>
              )}
            </View>
          )}

          <Text style={styles.sectionTitle}>Eventos</Text>

          {loadingEvents && !events ? (
            <View style={styles.eventsLoading}>
              <ActivityIndicator size="small" color="#FF5B8F" />
            </View>
          ) : displayEvents.length === 0 ? (
            <View style={styles.card}>
              <View style={styles.emptyEvents}>
                <ThemedIcon name="calendar-outline" size={40} color="#C7C7C7" />
                <Text style={styles.emptyEventsText}>Nenhum evento nos próximos dias</Text>
              </View>
              <View style={styles.cardDivider} />
              <TouchableOpacity
                style={styles.footerLink}
                onPress={() => navigation.navigate("Agenda")}
                accessibilityLabel="Verificar agenda completa"
                accessibilityRole="button"
              >
                <Text style={styles.footerLinkText}>Verificar agenda completa</Text>
                <ThemedIcon name="arrow-forward" size={16} color="#FF5B8F" />
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.card}>
              {displayEvents.map((event, index) => (
                <View key={event.id}>
                  <View style={styles.eventRow}>
                    <View style={styles.eventInfo}>
                      <Text style={styles.eventTitle}>{event.title}</Text>
                      <Text style={styles.eventCategory}>{event.category}</Text>
                    </View>
                    <View style={styles.eventDaysBadge}>
                      <Text style={styles.eventDaysText}>
                        {event.days_remaining <= 0
                          ? "Hoje"
                          : event.days_remaining === 1
                            ? "Amanhã"
                            : `Em ${event.days_remaining} dias`}
                      </Text>
                    </View>
                  </View>
                  {index < displayEvents.length - 1 && <View style={styles.cardDivider} />}
                </View>
              ))}
              <View style={styles.cardDivider} />
              <TouchableOpacity
                style={styles.footerLink}
                onPress={() => navigation.navigate("Agenda")}
                accessibilityLabel="Verificar agenda completa"
                accessibilityRole="button"
              >
                <Text style={styles.footerLinkText}>Verificar agenda completa</Text>
                <ThemedIcon name="arrow-forward" size={16} color="#FF5B8F" />
              </TouchableOpacity>
            </View>
          )}

          <Text style={styles.sectionTitle}>Carteira</Text>
          <TouchableOpacity
            style={styles.card}
            onPress={() => navigation.navigate("Wallet")}
            activeOpacity={0.7}
            accessibilityLabel="Acessar carteira"
            accessibilityRole="button"
          >
            <View style={styles.walletPreviewRow}>
              <View style={styles.walletIconContainer}>
                <ThemedIcon name="wallet-outline" size={24} color="#FF5B8F" />
              </View>
              <View style={styles.walletPreviewInfo}>
                <Text style={styles.walletLabel}>Saldo disponível</Text>
                {loadingWallet ? (
                  <ActivityIndicator size="small" color="#FF5B8F" />
                ) : (
                  <Text style={styles.walletAmount}>
                    R$ {(saldo ?? 0).toFixed(2)}
                  </Text>
                )}
              </View>
              <ThemedIcon name="chevron-forward" size={20} color="#C7C7C7" />
            </View>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    </View>
  );
}

const styles = createThemedStyles({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F7",
  },
  safeArea: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 32,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  statusText: {
    color: "#888",
    fontSize: 16,
    marginTop: 16,
    fontWeight: "500",
  },
  errorText: {
    color: "#333",
    fontSize: 15,
    fontWeight: "500",
    textAlign: "center",
  },
  retryButton: {
    borderWidth: 2,
    borderColor: "#FF5B8F",
    borderRadius: 999,
    paddingHorizontal: 24,
    paddingVertical: 12,
    marginTop: 24,
  },
  retryText: {
    color: "#FF5B8F",
    fontSize: 16,
    fontWeight: "600",
  },
  headerTitle: {
    fontSize: 40,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 24,
  },
  statsRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    borderRadius: 20,
    padding: 16,
    alignItems: "center",
  },
  statLabel: {
    fontSize: 13,
    color: "#7A7A7A",
    fontWeight: "500",
    marginBottom: 4,
  },
  statValue: {
    fontSize: 28,
    fontWeight: "700",
  },
  heroCard: {
    borderRadius: 40,
    padding: 18,
    paddingBottom: 16,
    marginBottom: 24,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.2)",
    ...Platform.select({
      ios: {
        shadowColor: "#FF5B8F",
        shadowOffset: { width: 0, height: 10 },
        shadowOpacity: 0.4,
        shadowRadius: 32,
      },
      android: {
        elevation: 16,
      },
    }),
  },
  decorGlow1: {
    position: "absolute",
    top: -40,
    right: -30,
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: "rgba(255,255,255,0.06)",
  },
  decorGlow2: {
    position: "absolute",
    bottom: -30,
    left: -30,
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: "rgba(255,255,255,0.04)",
  },
  decorGlow3: {
    position: "absolute",
    top: 30,
    left: "50%",
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: "rgba(255,255,255,0.06)",
  },
  decorDot1: {
    position: "absolute",
    top: 20,
    right: 30,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "rgba(255,255,255,0.3)",
  },
  decorDot2: {
    position: "absolute",
    bottom: 50,
    right: 50,
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: "rgba(255,255,255,0.2)",
  },
  decorDot3: {
    position: "absolute",
    top: 10,
    left: 60,
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: "rgba(255,255,255,0.2)",
  },
  atenaGlass: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 24,
    padding: 6,
    marginBottom: 4,
    gap: 8,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.2)",
  },
  atenaImage: {
    width: 60,
    height: 60,
    borderRadius: 16,
    ...Platform.select({
      ios: {
        shadowColor: "#FF5B8F",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.5,
        shadowRadius: 6,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  atenaTextGroup: {
    flex: 1,
    gap: 2,
  },
  atenaGreeting: {
    fontSize: 16,
    fontWeight: "700",
    color: "white",
  },
  atenaSubtitle: {
    fontSize: 12,
    color: "rgba(255,255,255,0.7)",
    fontWeight: "500",
  },
  atenaHighlight: {
    fontWeight: "800",
    color: "white",
  },
  atenaButton: {
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 999,
    height: 46,
    justifyContent: "center",
    marginBottom: 10,
    ...Platform.select({
      ios: {
        shadowColor: "white",
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.25,
        shadowRadius: 10,
      },
      android: {
        elevation: 6,
      },
    }),
  },
  atenaButtonText: {
    color: "#FF5B8F",
    fontSize: 15,
    fontWeight: "800",
  },
  liberarButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255,255,255,0.12)",
    borderRadius: 999,
    height: 40,
    gap: 6,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.15)",
  },
  liberarButtonText: {
    color: "rgba(255,255,255,0.85)",
    fontSize: 14,
    fontWeight: "700",
  },
  carteirinhaLink: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingTop: 10,
    paddingBottom: 2,
  },
  carteirinhaLinkText: {
    color: "rgba(255,255,255,0.5)",
    fontSize: 13,
    fontWeight: "600",
  },
  heroHeadline: {
    fontSize: 22,
    fontWeight: "500",
    color: "white",
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1F1F1F",
    marginBottom: 12,
  },
  eventsLoading: {
    padding: 20,
    alignItems: "center",
  },
  eventInfo: {
    flex: 1,
    marginRight: 12,
  },
  eventTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  eventCategory: {
    fontSize: 13,
    color: "#7A7A7A",
    marginTop: 2,
  },
  eventDaysBadge: {
    backgroundColor: "#FF5B8F",
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 5,
  },
  eventDaysText: {
    color: "white",
    fontSize: 12,
    fontWeight: "700",
  },
  card: {
    backgroundColor: "white",
    borderRadius: 36,
    padding: 24,
    marginBottom: 20,
  },
  cardDivider: {
    height: 1,
    backgroundColor: "#E5E5E5",
  },
  eventRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 16,
  },
  footerLink: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingTop: 16,
    gap: 6,
  },
  footerLinkText: {
    color: "#FF5B8F",
    fontSize: 14,
    fontWeight: "600",
  },
  walletPreviewRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  walletIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#FFF0F3",
    justifyContent: "center",
    alignItems: "center",
  },
  walletPreviewInfo: {
    flex: 1,
  },
  walletLabel: {
    fontSize: 14,
    color: "#7A7A7A",
    fontWeight: "500",
    marginBottom: 4,
  },
  walletAmount: {
    fontSize: 28,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  freqDetailCard: {
    backgroundColor: "white",
    borderRadius: 20,
    padding: 16,
    marginBottom: 24,
  },
  hojeRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 12,
  },
  hojeText: {
    fontSize: 15,
    fontWeight: "600",
  },
  progressContainer: {
    marginBottom: 12,
  },
  progressBg: {
    height: 10,
    borderRadius: 5,
    backgroundColor: "#E5E5E5",
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: 5,
  },
  freqBreakdown: {
    flexDirection: "row",
    justifyContent: "space-around",
  },
  freqBreakdownItem: {
    fontSize: 13,
    color: "#7A7A7A",
  },
  emptyEvents: {
    alignItems: "center",
    paddingVertical: 16,
    gap: 8,
  },
  emptyEventsText: {
    fontSize: 14,
    color: "#C7C7C7",
    fontWeight: "500",
  },
});
