import { memo } from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { LoginScreen } from "../screens/LoginScreen";
import { useAuth } from "../contexts/AuthContext";
import { ProfileRouter } from "./ProfileRouter";

type AuthStackParamList = {
  Login: undefined;
};

const Stack = createNativeStackNavigator<AuthStackParamList>();

const AuthStack = memo(function AuthStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Login" component={LoginScreen} />
    </Stack.Navigator>
  );
});

export function RootNavigator() {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <ProfileRouter /> : <AuthStack />;
}
