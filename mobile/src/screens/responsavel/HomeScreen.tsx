import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
  SafeAreaView,
} from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { useDashboard } from "../../hooks/useDashboard";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { useEvents } from "../../hooks/useAgenda";
import { useWallet } from "../../hooks/useWallet";
import type { ResponsavelStackParamList } from "../../types/navigation";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "HomeTabs">;

const MOCK_EVENTS: Array<{ id: string; title: string; category: string; days_remaining: number }> = [
  { id: "mock-1", title: "Excursão", category: "Escola", days_remaining: 3 },
  { id: "mock-2", title: "Reunião de pais", category: "Escola", days_remaining: 5 },
  { id: "mock-3", title: "Prova", category: "Matemática", days_remaining: 7 },
];

function daysUntil(dateStr: string): number {
  const now = new Date();
  const target = new Date(dateStr);
  const diff = target.getTime() - now.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

export function HomeScreen() {
  const navigation = useNavigation<NavProp>();
  const { data: dashboard, loading, error, refetch } = useDashboard();
  const { selectedChild } = useSelectedStudent();
  const { events, loading: loadingEvents } = useEvents({ size: 5 });
  const { saldo, loading: loadingWallet } = useWallet();

  if (loading) {
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

  if (error) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <View style={styles.center}>
            <Ionicons name="alert-circle-outline" size={56} color="#FF5B8F" />
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity style={styles.retryButton} onPress={refetch}>
              <Text style={styles.retryText}>Tentar novamente</Text>
            </TouchableOpacity>
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
  const hasRealEvents = eventList.length > 0;
  const displayEvents = hasRealEvents
    ? eventList.slice(0, 5).map((e) => ({
        id: e.id,
        title: e.titulo,
        category: "Evento",
        days_remaining: daysUntil(e.data_inicio),
      }))
    : MOCK_EVENTS;

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <Text style={styles.headerTitle}>Resumo</Text>

          <LinearGradient
            colors={["#F84F8D", "#FF8664"]}
            start={{ x: 0, y: 0.5 }}
            end={{ x: 1, y: 0.5 }}
            style={styles.heroCard}
          >
            <View style={styles.heroContent}>
              <View style={styles.heroAvatar}>
                <Text style={styles.heroAvatarText}>
                  {selectedChild.aluno_nome.charAt(0).toUpperCase()}
                </Text>
              </View>
              <View style={styles.heroTextGroup}>
                <Text style={styles.heroHeadline}>Hoje tem aula!</Text>
                <TouchableOpacity
                  style={styles.heroButton}
                  onPress={() => navigation.navigate("Boletim")}
                >
                  <Text style={styles.heroButtonText}>Ver boletim</Text>
                </TouchableOpacity>
              </View>
            </View>
          </LinearGradient>

          <Text style={styles.sectionTitle}>Eventos</Text>

          {loadingEvents && !hasRealEvents ? (
            <View style={styles.eventsLoading}>
              <ActivityIndicator size="small" color="#FF5B8F" />
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
              >
                <Text style={styles.footerLinkText}>Verificar agenda completa</Text>
                <Ionicons name="arrow-forward" size={16} color="#FF5B8F" />
              </TouchableOpacity>
            </View>
          )}

          <Text style={styles.sectionTitle}>Carteira</Text>
          <TouchableOpacity
            style={styles.card}
            onPress={() => navigation.navigate("Wallet")}
            activeOpacity={0.7}
          >
            <View style={styles.walletMainRow}>
              <Text style={styles.walletLabel}>Saldo disponível</Text>
              {loadingWallet ? (
                <ActivityIndicator size="small" color="#FF5B8F" />
              ) : (
                <Text style={styles.walletAmount}>
                  R$ {(saldo ?? 0).toFixed(2)}
                </Text>
              )}
            </View>
            <View style={styles.cardDivider} />
            <View style={styles.footerLink}>
              <Text style={styles.footerLinkText}>Ver carteira</Text>
              <Ionicons name="arrow-forward" size={16} color="#FF5B8F" />
            </View>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
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
  heroCard: {
    borderRadius: 40,
    minHeight: 180,
    padding: 24,
    marginBottom: 24,
  },
  heroContent: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 20,
  },
  heroAvatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "rgba(255,255,255,0.25)",
    justifyContent: "center",
    alignItems: "center",
  },
  heroAvatarText: {
    color: "white",
    fontSize: 30,
    fontWeight: "700",
  },
  heroTextGroup: {
    flex: 1,
    gap: 16,
  },
  heroHeadline: {
    fontSize: 22,
    fontWeight: "500",
    color: "white",
  },
  heroButton: {
    backgroundColor: "white",
    borderRadius: 999,
    height: 44,
    paddingHorizontal: 24,
    alignSelf: "flex-start",
    justifyContent: "center",
    alignItems: "center",
  },
  heroButtonText: {
    color: "#FF5B8F",
    fontSize: 15,
    fontWeight: "700",
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
  walletMainRow: {
    paddingVertical: 8,
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
  walletFutureRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 16,
  },
  walletFutureLabel: {
    fontSize: 15,
    color: "#1F1F1F",
    fontWeight: "500",
  },
  walletFutureValue: {
    fontSize: 15,
    color: "#C7C7C7",
    fontWeight: "500",
  },
});
