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
import { useStatement } from "../../hooks/useWallet";
import type { MovimentacaoItem } from "../../api/financial.service";
import type { ResponsavelStackParamList } from "../../types/navigation";

type NavProp = NativeStackNavigationProp<ResponsavelStackParamList, "Statement">;

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

function MovementIcon({ tipo }: { tipo: string }) {
  switch (tipo) {
    case "recarga":
      return <Ionicons name="add-circle" size={24} color="#4CAF50" />;
    case "consumo":
      return <Ionicons name="remove-circle" size={24} color="#FF5B8F" />;
    case "estorno":
      return <Ionicons name="refresh-circle" size={24} color="#FF9800" />;
    default:
      return <Ionicons name="ellipse" size={24} color="#C7C7C7" />;
  }
}

function MovementRow({ item }: { item: MovimentacaoItem }) {
  const isCredit = item.tipo === "recarga" || item.tipo === "estorno";
  return (
    <View style={styles.movementRow}>
      <MovementIcon tipo={item.tipo} />
      <View style={styles.movementInfo}>
        <Text style={styles.movementType}>
          {item.tipo === "recarga"
            ? "Recarga"
            : item.tipo === "consumo"
              ? "Consumo"
              : "Estorno"}
        </Text>
        {item.descricao ? (
          <Text style={styles.movementDesc}>{item.descricao}</Text>
        ) : null}
        <Text style={styles.movementDate}>
          {formatDate(item.created_at)} às {formatTime(item.created_at)}
        </Text>
      </View>
      <View style={styles.movementValue}>
        <Text
          style={[
            styles.movementAmount,
            { color: isCredit ? "#4CAF50" : "#FF5B8F" },
          ]}
        >
          {isCredit ? "+" : "-"}R$ {item.valor.toFixed(2)}
        </Text>
      </View>
    </View>
  );
}

export function StatementScreen() {
  const navigation = useNavigation<NavProp>();
  const { extrato, loading, error, refetch } = useStatement();

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Ionicons name="chevron-back" size={28} color="#1F1F1F" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Extrato</Text>
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
            data={extrato?.movimentacoes ?? []}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => <MovementRow item={item} />}
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
                <Ionicons name="wallet-outline" size={48} color="#C7C7C7" />
                <Text style={styles.emptyText}>Nenhuma movimentação</Text>
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
  movementRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 20,
    padding: 16,
    marginBottom: 8,
  },
  movementInfo: {
    flex: 1,
    marginLeft: 12,
  },
  movementType: {
    fontSize: 15,
    fontWeight: "600",
    color: "#1F1F1F",
  },
  movementDesc: {
    fontSize: 13,
    color: "#7A7A7A",
    marginTop: 2,
  },
  movementDate: {
    fontSize: 12,
    color: "#C7C7C7",
    marginTop: 4,
  },
  movementValue: {
    alignItems: "flex-end",
  },
  movementAmount: {
    fontSize: 16,
    fontWeight: "700",
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
