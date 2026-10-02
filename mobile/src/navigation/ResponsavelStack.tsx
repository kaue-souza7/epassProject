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
import { LiberarAlunoScreen } from "../screens/responsavel/LiberarAlunoScreen";
import { AtenaChatScreen } from "../screens/responsavel/AtenaChatScreen";
import { CarteirinhaDigitalScreen } from "../screens/responsavel/CarteirinhaDigitalScreen";
import { CantinaScreen } from "../screens/responsavel/CantinaScreen";
import { MontarLancheScreen } from "../screens/responsavel/MontarLancheScreen";
import { PersonalizarSemanaScreen } from "../screens/responsavel/PersonalizarSemanaScreen";
import { PedidoStatusScreen } from "../screens/responsavel/PedidoStatusScreen";
import { PedidoHistoricoScreen } from "../screens/responsavel/PedidoHistoricoScreen";
import { OcorrenciaDetalheScreen } from "../screens/responsavel/OcorrenciaDetalheScreen";
import { EditarPerfilScreen } from "../screens/responsavel/EditarPerfilScreen";
import { NotificacoesScreen } from "../screens/responsavel/NotificacoesScreen";
import { SolicitarDocumentosScreen } from "../screens/responsavel/SolicitarDocumentosScreen";
import { AcessibilidadeScreen } from "../screens/responsavel/AcessibilidadeScreen";
import { fade, modal, push } from "./transitions";

const Stack = createNativeStackNavigator<ResponsavelStackParamList>();

export function ResponsavelStack() {
  return (
    <Stack.Navigator initialRouteName="SelectStudent" screenOptions={push}>
      <Stack.Screen name="SelectStudent" component={SelectStudentPlaceholder} />
      <Stack.Screen name="HomeTabs" component={ResponsavelTabNavigator} />
      <Stack.Screen name="Boletim" component={BoletimScreen} />
      <Stack.Screen name="BoletimAnual" component={BoletimAnualScreen} />
      <Stack.Screen name="Agenda" component={AgendaScreen} />
      <Stack.Screen name="Wallet" component={WalletScreen} />
      <Stack.Screen name="Statement" component={StatementScreen} options={modal} />
      <Stack.Screen name="Recharge" component={RechargeScreen} options={modal} />
      <Stack.Screen name="LiberarAluno" component={LiberarAlunoScreen} />
      <Stack.Screen name="AtenaChat" component={AtenaChatScreen} options={fade} />
      <Stack.Screen
        name="CarteirinhaDigital"
        component={CarteirinhaDigitalScreen}
        options={modal}
      />
      <Stack.Screen name="Cantina" component={CantinaScreen} />
      <Stack.Screen name="MontarLanche" component={MontarLancheScreen} options={modal} />
      <Stack.Screen
        name="PersonalizarSemana"
        component={PersonalizarSemanaScreen}
        options={modal}
      />
      <Stack.Screen name="PedidoStatus" component={PedidoStatusScreen} />
      <Stack.Screen name="PedidoHistorico" component={PedidoHistoricoScreen} />
      <Stack.Screen name="OcorrenciaDetalhe" component={OcorrenciaDetalheScreen} />
      <Stack.Screen name="EditarPerfil" component={EditarPerfilScreen} />
      <Stack.Screen name="Notificacoes" component={NotificacoesScreen} />
      <Stack.Screen
        name="SolicitarDocumentos"
        component={SolicitarDocumentosScreen}
      />
      <Stack.Screen name="Acessibilidade" component={AcessibilidadeScreen} />
    </Stack.Navigator>
  );
}
