import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import type { BottomTabBarProps } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { ProfessorResumoScreen } from "../screens/professor/ProfessorResumoScreen";
import { ProfessorModulosScreen } from "../screens/professor/ProfessorModulosScreen";
import { PerfilScreen } from "../screens/responsavel/PerfilScreen";
import type { ProfessorTabParamList } from "../types/navigation";

const Tab = createBottomTabNavigator<ProfessorTabParamList>();

const TAB_ICONS: Record<string, keyof typeof Ionicons.glyphMap> = {
  Resumo: "home",
  Modulos: "grid",
  Perfil: "person",
};

const TAB_LABELS: Record<string, string> = {
  Resumo: "Resumo",
  Modulos: "Módulos",
  Perfil: "Perfil",
};

function CustomTabBar(props: BottomTabBarProps) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.tabBarContainer, { paddingBottom: insets.bottom + 8 }]}>
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

export function ProfessorTabNavigator() {
  return (
    <Tab.Navigator
      tabBar={(props) => <CustomTabBar {...props} />}
      screenOptions={{ headerShown: false }}
    >
      <Tab.Screen name="Resumo" component={ProfessorResumoScreen} />
      <Tab.Screen name="Modulos" component={ProfessorModulosScreen} />
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
});
