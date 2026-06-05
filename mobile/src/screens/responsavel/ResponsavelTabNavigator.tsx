import { useState, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
} from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import type { BottomTabBarProps } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useDashboard } from "../../hooks/useDashboard";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { HomeScreen } from "./HomeScreen";
import { RelatoriosScreen } from "./RelatoriosScreen";
import { AvisosScreen } from "./AvisosScreen";
import { PerfilScreen } from "./PerfilScreen";
import type { Child } from "../../types/responsavel";

type ResponsavelTabParamList = {
  HomeTab: undefined;
  Relatorios: undefined;
  Avisos: undefined;
  Perfil: undefined;
};

const Tab = createBottomTabNavigator<ResponsavelTabParamList>();

const TAB_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  HomeTab: "home",
  Relatorios: "document-text",
  Avisos: "chatbubble-outline",
  Perfil: "person",
};

const TAB_LABELS: Record<string, string> = {
  HomeTab: "Resumo",
  Relatorios: "Relatório",
  Avisos: "Avisos",
  Perfil: "Perfil",
};

function StudentSelector() {
  const [expanded, setExpanded] = useState(false);
  const anim = useRef(new Animated.Value(0)).current;
  const { data } = useDashboard();
  const { selectedChild, selectChild } = useSelectedStudent();

  const filhos = data?.filhos ?? [];
  const hasMultiple = filhos.length > 1;

  const toggle = () => {
    if (!hasMultiple) return;
    Animated.timing(anim, {
      toValue: expanded ? 0 : 1,
      duration: 250,
      useNativeDriver: false,
    }).start();
    setExpanded(!expanded);
  };

  const handleSelect = (child: Child) => {
    selectChild(child);
    Animated.timing(anim, {
      toValue: 0,
      duration: 200,
      useNativeDriver: false,
    }).start();
    setExpanded(false);
  };

  const maxHeight = anim.interpolate({
    inputRange: [0, 1],
    outputRange: [0, 180],
  });

  if (!selectedChild) return null;

  return (
    <View style={styles.selectorOuter}>
      <TouchableOpacity
        style={styles.selectorCard}
        onPress={toggle}
        activeOpacity={hasMultiple ? 0.7 : 1}
        accessibilityLabel={`Aluno selecionado: ${selectedChild.aluno_nome}${hasMultiple ? ". Toque para trocar de aluno." : ""}`}
        accessibilityRole="button"
      >
        <View style={styles.selectorAvatar}>
          <Text style={styles.selectorAvatarText}>
            {selectedChild.aluno_nome.charAt(0).toUpperCase()}
          </Text>
        </View>
        <View style={styles.selectorInfo}>
          <Text style={styles.selectorName} numberOfLines={1}>
            {selectedChild.aluno_nome}
          </Text>
          {selectedChild.turma_codigo && (
            <Text style={styles.selectorClass}>
              {selectedChild.turma_codigo}
            </Text>
          )}
        </View>
        {hasMultiple && (
          <Ionicons
            name={expanded ? "chevron-up" : "chevron-down"}
            size={20}
            color="#999"
          />
        )}
      </TouchableOpacity>

      <Animated.View style={[styles.expandArea, { maxHeight }]}>
        {expanded && (
          <View style={styles.expandInner}>
            {filhos
              .filter((f) => f.aluno_id !== selectedChild.aluno_id)
              .map((child) => (
                <TouchableOpacity
                  key={child.aluno_id}
                  style={styles.childRow}
                  onPress={() => handleSelect(child)}
                  activeOpacity={0.7}
                >
                  <View style={styles.childRowAvatar}>
                    <Text style={styles.childRowAvatarText}>
                      {child.aluno_nome.charAt(0).toUpperCase()}
                    </Text>
                  </View>
                  <View style={styles.childRowInfo}>
                    <Text style={styles.childRowName} numberOfLines={1}>
                      {child.aluno_nome}
                    </Text>
                    {child.turma_codigo && (
                      <Text style={styles.childRowClass}>
                        {child.turma_codigo}
                      </Text>
                    )}
                  </View>
                </TouchableOpacity>
              ))}
          </View>
        )}
      </Animated.View>
    </View>
  );
}

function CustomTabBar(props: BottomTabBarProps) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.tabBarContainer, { paddingBottom: insets.bottom + 8 }]}>
      <StudentSelector />
      <View style={styles.tabBar}>
        {props.state.routes.map((route, index) => {
          const focused = index === props.state.index;
          const color = focused ? "#FF5B8F" : "#B0B0B0";
          return (
            <TouchableOpacity
              key={route.key}
              style={styles.tabItem}
              onPress={() => props.navigation.navigate(route.name)}
              activeOpacity={0.7}
              accessibilityLabel={TAB_LABELS[route.name] ?? route.name}
              accessibilityRole="tab"
            >
              <Ionicons
                name={TAB_ICONS[route.name] ?? "ellipse"}
                size={20}
                color={color}
              />
              <Text style={[styles.tabLabel, { color }]}>
                {TAB_LABELS[route.name] ?? route.name}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

export function ResponsavelTabNavigator() {
  return (
    <Tab.Navigator
      tabBar={(props) => <CustomTabBar {...props} />}
      screenOptions={{
        headerShown: false,
      }}
    >
      <Tab.Screen name="HomeTab" component={HomeScreen} />
      <Tab.Screen name="Relatorios" component={RelatoriosScreen} />
      <Tab.Screen name="Avisos" component={AvisosScreen} />
      <Tab.Screen name="Perfil" component={PerfilScreen} />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  tabBarContainer: {
    position: "absolute",
    left: 16,
    right: 16,
    bottom: 0,
  },
  tabBar: {
    flexDirection: "row",
    backgroundColor: "white",
    borderRadius: 48,
    paddingVertical: 6,
    paddingHorizontal: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 8,
  },
  tabItem: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 4,
    gap: 2,
  },
  tabLabel: {
    fontSize: 10,
    fontWeight: "600",
  },
  selectorOuter: {
    marginBottom: 8,
  },
  selectorCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "white",
    borderRadius: 32,
    paddingVertical: 8,
    paddingHorizontal: 14,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  selectorAvatar: {
    width: 32,
    height: 32,
    borderRadius: 22,
    backgroundColor: "#FF5B8F",
    justifyContent: "center",
    alignItems: "center",
  },
  selectorAvatarText: {
    color: "white",
    fontSize: 14,
    fontWeight: "700",
  },
  selectorInfo: {
    flex: 1,
    marginLeft: 10,
  },
  selectorName: {
    fontSize: 14,
    fontWeight: "700",
    color: "#333",
  },
  selectorClass: {
    fontSize: 12,
    color: "#888",
    marginTop: 1,
  },
  expandArea: {
    overflow: "hidden",
  },
  expandInner: {
    backgroundColor: "white",
    borderBottomLeftRadius: 32,
    borderBottomRightRadius: 32,
    paddingBottom: 8,
    paddingHorizontal: 14,
    marginTop: -4,
  },
  childRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: "#F0F0F0",
  },
  childRowAvatar: {
    width: 34,
    height: 34,
    borderRadius: 22,
    backgroundColor: "#FCE4EC",
    justifyContent: "center",
    alignItems: "center",
  },
  childRowAvatarText: {
    color: "#FF5B8F",
    fontSize: 14,
    fontWeight: "700",
  },
  childRowInfo: {
    flex: 1,
    marginLeft: 10,
  },
  childRowName: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
  },
  childRowClass: {
    fontSize: 12,
    color: "#888",
    marginTop: 1,
  },
});
