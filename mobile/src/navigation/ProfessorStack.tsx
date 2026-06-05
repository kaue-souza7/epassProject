import { createNativeStackNavigator } from "@react-navigation/native-stack";
import type { ProfessorStackParamList } from "../types/navigation";
import { ProfessorTabNavigator } from "./ProfessorTabNavigator";
import { TurmaAlunosScreen } from "../screens/professor/TurmaAlunosScreen";
import { LancarFrequenciaScreen } from "../screens/professor/LancarFrequenciaScreen";
import { LancarNotasScreen } from "../screens/professor/LancarNotasScreen";

const Stack = createNativeStackNavigator<ProfessorStackParamList>();

export function ProfessorStack() {
  return (
    <Stack.Navigator
      initialRouteName="ProfessorTabs"
      screenOptions={{ headerShown: false }}
    >
      <Stack.Screen name="ProfessorTabs" component={ProfessorTabNavigator} />
      <Stack.Screen name="TurmaAlunos" component={TurmaAlunosScreen} />
      <Stack.Screen name="LancarFrequencia" component={LancarFrequenciaScreen} />
      <Stack.Screen name="LancarNotas" component={LancarNotasScreen} />
    </Stack.Navigator>
  );
}
