import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { ProfessorResumoScreen } from "../screens/professor/ProfessorResumoScreen";
import { ProfessorModulosScreen } from "../screens/professor/ProfessorModulosScreen";
import { PerfilScreen } from "../screens/responsavel/PerfilScreen";
import type { ProfessorTabParamList } from "../types/navigation";
import { AnimatedTabBar, type AnimatedTab } from "./AnimatedTabBar";

const Tab = createBottomTabNavigator<ProfessorTabParamList>();

const TABS: Record<string, AnimatedTab> = {
  Resumo: { label: "Resumo", icon: "home" },
  Modulos: { label: "Módulos", icon: "grid" },
  Perfil: { label: "Perfil", icon: "person" },
};

export function ProfessorTabNavigator() {
  return (
    <Tab.Navigator
      tabBar={(props) => <AnimatedTabBar {...props} tabs={TABS} />}
      screenOptions={{ headerShown: false }}
    >
      <Tab.Screen name="Resumo" component={ProfessorResumoScreen} />
      <Tab.Screen name="Modulos" component={ProfessorModulosScreen} />
      <Tab.Screen name="Perfil" component={PerfilScreen} />
    </Tab.Navigator>
  );
}
