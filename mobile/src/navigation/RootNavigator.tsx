import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { LoginScreen } from "../screens/LoginScreen";
import { useAuth } from "../contexts/AuthContext";
import { ProfileRouter } from "./ProfileRouter";

const Stack = createNativeStackNavigator();

function AuthStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={LoginScreen} />
    </Stack.Navigator>
  );
}

export function RootNavigator() {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <ProfileRouter /> : <AuthStack />;
}
