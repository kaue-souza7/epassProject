import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  FlatList,
  SafeAreaView,
  RefreshControl,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useEvents } from "../../hooks/useAgenda";
import type { AgendaEvent } from "../../types/responsavel";
import type { ResponsavelStackParamList } from "../../types/navigation";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "Agenda">;

const PAGE_SIZE = 100;

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDateWithTime(dateStr: string): string {
  return `${formatDate(dateStr)} às ${formatTime(dateStr)}`;
}

function EventCard({ item }: { item: AgendaEvent }) {
  return (
    <View style={styles.eventCard}>
      <View style={styles.eventIcon}>
        <Ionicons name="calendar-outline" size={22} color="#FF5B8F" />
      </View>
      <View style={styles.eventInfo}>
        <Text style={styles.eventTitle}>{item.titulo}</Text>
        <Text style={styles.eventDate}>
          {formatDateWithTime(item.data_inicio)}
        </Text>
        {item.local ? (
          <Text style={styles.eventLocal}>{item.local}</Text>
        ) : null}
      </View>
    </View>
  );
}

export function AgendaScreen() {
  const navigation = useNavigation<NavProp>();
  const { events, loading, error, refetch } = useEvents({ size: PAGE_SIZE });

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Ionicons name="chevron-back" size={28} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Agenda</Text>
          <View style={{ width: 28 }} />
        </View>

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#FF5B8F" />
          </View>
        ) : error ? (
          <View style={styles.center}>
            <Ionicons name="alert-circle-outline" size={56} color="#FF5B8F" />
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity style={styles.retryButton} onPress={refetch}>
              <Text style={styles.retryText}>Tentar novamente</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <FlatList
            data={events?.items ?? []}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => <EventCard item={item} />}
            contentContainerStyle={styles.list}
            refreshControl={
              <RefreshControl
                refreshing={loading}
                onRefresh={refetch}
                tintColor="#FF5B8F"
              />
            }
            ListEmptyComponent={
              <View style={styles.emptyContainer}>
                <Ionicons name="calendar-outline" size={48} color="#C7C7C7" />
                <Text style={styles.emptyText}>Nenhum evento</Text>
              </View>
            }
          />
        )}
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
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 24,
    paddingVertical: 16,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  errorText: {
    color: "#333",
    fontSize: 15,
    fontWeight: "500",
    textAlign: "center",
    marginTop: 16,
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
  list: {
    paddingHorizontal: 24,
    paddingBottom: 32,
  },
  eventCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 20,
    padding: 16,
    marginBottom: 8,
  },
  eventIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#FFF0F3",
    justifyContent: "center",
    alignItems: "center",
  },
  eventInfo: {
    flex: 1,
    marginLeft: 12,
  },
  eventTitle: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  eventDate: {
    fontSize: 13,
    color: "#7A7A7A",
    fontWeight: "500",
    marginTop: 2,
  },
  eventLocal: {
    fontSize: 12,
    color: "#C7C7C7",
    fontWeight: "500",
    marginTop: 2,
  },
  emptyContainer: {
    alignItems: "center",
    paddingTop: 80,
  },
  emptyText: {
    fontSize: 16,
    color: "#C7C7C7",
    fontWeight: "500",
    marginTop: 16,
  },
});
