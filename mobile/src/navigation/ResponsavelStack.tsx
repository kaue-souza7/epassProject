import { createNativeStackNavigator } from "@react-navigation/native-stack";
import type { ResponsavelStackParamList } from "../types/navigation";
import { SelectStudentPlaceholder } from "../screens/responsavel/SelectStudentPlaceholder";
import { ResponsavelTabNavigator } from "../screens/responsavel/ResponsavelTabNavigator";
import { BoletimScreen } from "../screens/responsavel/BoletimScreen";
import { BoletimAnualScreen } from "../screens/responsavel/BoletimAnualScreen";
import { AgendaScreen } from "../screens/responsavel/AgendaScreen";
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
      <Stack.Screen name="HomeTabs" component={ResponsavelTabNavigator} />
      <Stack.Screen name="Boletim" component={BoletimScreen} />
      <Stack.Screen name="BoletimAnual" component={BoletimAnualScreen} />
      <Stack.Screen name="Agenda" component={AgendaScreen} />
      <Stack.Screen name="Wallet" component={WalletScreen} />
      <Stack.Screen name="Statement" component={StatementScreen} />
      <Stack.Screen name="Recharge" component={RechargeScreen} />
    </Stack.Navigator>
  );
}
