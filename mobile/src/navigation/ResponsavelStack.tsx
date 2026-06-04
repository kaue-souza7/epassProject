import { createNativeStackNavigator } from "@react-navigation/native-stack";
import type { ResponsavelStackParamList } from "../types/navigation";
import { SelectStudentPlaceholder } from "../screens/responsavel/SelectStudentPlaceholder";
import { HomePlaceholder } from "../screens/responsavel/HomePlaceholder";
import { BoletimScreen } from "../screens/responsavel/BoletimScreen";
import { AgendaScreen } from "../screens/responsavel/AgendaScreen";
import { PerfilScreen } from "../screens/responsavel/PerfilScreen";
import { WalletScreen } from "../screens/responsavel/WalletScreen";
import { StatementScreen } from "../screens/responsavel/StatementScreen";
import { RechargeScreen } from "../screens/responsavel/RechargeScreen";

const Stack = createNativeStackNavigator<ResponsavelStackParamList>();

export function ResponsavelStack() {
  return (
    <Stack.Navigator
      initialRouteName="SelectStudent"
      screenOptions={{ headerShown: false }}
    >
      <Stack.Screen name="SelectStudent" component={SelectStudentPlaceholder} />
      <Stack.Screen name="HomeTabs" component={HomePlaceholder} />
      <Stack.Screen name="Boletim" component={BoletimScreen} />
      <Stack.Screen name="Agenda" component={AgendaScreen} />
      <Stack.Screen name="Perfil" component={PerfilScreen} />
      <Stack.Screen name="Wallet" component={WalletScreen} />
      <Stack.Screen name="Statement" component={StatementScreen} />
      <Stack.Screen name="Recharge" component={RechargeScreen} />
    </Stack.Navigator>
  );
}
