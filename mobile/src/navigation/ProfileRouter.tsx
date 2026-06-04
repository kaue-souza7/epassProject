import { useAuth } from "../contexts/AuthContext";
import { ResponsavelStack } from "./ResponsavelStack";
import { TabNavigator } from "./TabNavigator";

export function ProfileRouter() {
  const { user } = useAuth();

  if (user?.perfil === "responsavel") {
    return <ResponsavelStack />;
  }

  return <TabNavigator />;
}
