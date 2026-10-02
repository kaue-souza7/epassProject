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
import { useDashboard } from "../../hooks/useDashboard";
import { useNotificacoesNaoLidas } from "../../hooks/useCommunication";
import { useSelectedStudent } from "../../hooks/useSelectedStudent";
import { AnimatedTabBar, type AnimatedTab } from "../../navigation/AnimatedTabBar";
import { HomeScreen } from "./HomeScreen";
import { RelatoriosScreen } from "./RelatoriosScreen";
import { AvisosScreen } from "./AvisosScreen";
import { PerfilScreen } from "./PerfilScreen";
import type { Child } from "../../types/responsavel";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type ResponsavelTabParamList = {
  HomeTab: undefined;
  Relatorios: undefined;
  Avisos: { avisoId?: string } | undefined;
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
          <ThemedIcon
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
  const { total: naoLidas } = useNotificacoesNaoLidas();

  const tabs: Record<string, AnimatedTab> = {
    HomeTab: { label: TAB_LABELS.HomeTab, icon: TAB_ICONS.HomeTab },
    Relatorios: { label: TAB_LABELS.Relatorios, icon: TAB_ICONS.Relatorios },
    Avisos: {
      label: TAB_LABELS.Avisos,
      icon: TAB_ICONS.Avisos,
      badge: naoLidas > 0 ? naoLidas : undefined,
    },
    Perfil: { label: TAB_LABELS.Perfil, icon: TAB_ICONS.Perfil },
  };

  // O seletor de aluno não pertence ao perfil da conta: ele só faz sentido nas
  // abas de conteúdo do aluno. Além disso, a lista expansível sobrepunha o
  // cartão de perfil ao ser aberta.
  const rotaAtiva = props.state.routes[props.state.index]?.name;
  const header = rotaAtiva === "Perfil" ? undefined : <StudentSelector />;

  return <AnimatedTabBar {...props} tabs={tabs} header={header} />;
}

export function ResponsavelTabNavigator() {
  useThemeVersion();

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

const styles = createThemedStyles({
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
