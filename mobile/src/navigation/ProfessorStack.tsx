import { createNativeStackNavigator } from "@react-navigation/native-stack";
import type { ProfessorStackParamList } from "../types/navigation";
import { ProfessorTabNavigator } from "./ProfessorTabNavigator";
import { ClassesScreen } from "../screens/professor/ClassesScreen";
import { GabaritoHomeScreen } from "../screens/professor/GabaritoHomeScreen";
import { GabaritoTurmaScreen } from "../screens/professor/GabaritoTurmaScreen";
import { GabaritoAvaliacaoScreen } from "../screens/professor/GabaritoAvaliacaoScreen";
import { GabaritoCadastroScreen } from "../screens/professor/GabaritoCadastroScreen";
import { GabaritoScannerScreen } from "../screens/professor/GabaritoScannerScreen";
import { GabaritoProcessamentoScreen } from "../screens/professor/GabaritoProcessamentoScreen";
import { GabaritoRevisaoScreen } from "../screens/professor/GabaritoRevisaoScreen";
import { GabaritoResultadoScreen } from "../screens/professor/GabaritoResultadoScreen";
import { TurmaAlunosScreen } from "../screens/professor/TurmaAlunosScreen";
import { LancarFrequenciaScreen } from "../screens/professor/LancarFrequenciaScreen";
import { LancarNotasScreen } from "../screens/professor/LancarNotasScreen";
import { EditarPerfilScreen } from "../screens/responsavel/EditarPerfilScreen";
import { AcessibilidadeScreen } from "../screens/responsavel/AcessibilidadeScreen";
import { fade, modal, push, wizard } from "./transitions";

const Stack = createNativeStackNavigator<ProfessorStackParamList>();

export function ProfessorStack() {
  return (
    <Stack.Navigator initialRouteName="ProfessorTabs" screenOptions={push}>
      <Stack.Screen name="ProfessorTabs" component={ProfessorTabNavigator} />
      <Stack.Screen name="ClassesList" component={ClassesScreen} />
      <Stack.Screen name="GabaritoHome" component={GabaritoHomeScreen} />
      <Stack.Screen name="GabaritoTurma" component={GabaritoTurmaScreen} options={wizard} />
      <Stack.Screen name="GabaritoAvaliacao" component={GabaritoAvaliacaoScreen} options={wizard} />
      <Stack.Screen
        name="GabaritoCadastro"
        component={GabaritoCadastroScreen}
        options={modal}
      />
      <Stack.Screen
        name="GabaritoScanner"
        component={GabaritoScannerScreen}
        options={fade}
      />
      <Stack.Screen
        name="GabaritoProcessamento"
        component={GabaritoProcessamentoScreen}
        options={fade}
      />
      <Stack.Screen name="GabaritoRevisao" component={GabaritoRevisaoScreen} options={wizard} />
      <Stack.Screen
        name="GabaritoResultado"
        component={GabaritoResultadoScreen}
        options={fade}
      />
      <Stack.Screen name="TurmaAlunos" component={TurmaAlunosScreen} />
      <Stack.Screen
        name="LancarFrequencia"
        component={LancarFrequenciaScreen}
        options={modal}
      />
      <Stack.Screen name="LancarNotas" component={LancarNotasScreen} options={modal} />
      <Stack.Screen name="EditarPerfil" component={EditarPerfilScreen} />
      <Stack.Screen name="Acessibilidade" component={AcessibilidadeScreen} />
    </Stack.Navigator>
  );
}
