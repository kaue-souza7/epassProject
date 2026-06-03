import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { MaterialIcons } from "@expo/vector-icons";
import { View, Text } from "react-native";

const Tab = createBottomTabNavigator();

function PlaceholderTab({ label }: { label: string }) {
  return (
    <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
      <Text>{label}</Text>
    </View>
  );
}

export function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ color, size }) => {
          const icons: Record<string, keyof typeof MaterialIcons.glyphMap> = {
            Resumo: "dashboard",
            Boletim: "school",
            Financeiro: "account-balance-wallet",
            Perfil: "person",
          };
          return <MaterialIcons name={icons[route.name]} size={size} color={color} />;
        },
        tabBarActiveTintColor: "#FF5B8F",
        tabBarInactiveTintColor: "#999",
      })}
    >
      <Tab.Screen name="Resumo">
        {() => <PlaceholderTab label="Resumo" />}
      </Tab.Screen>
      <Tab.Screen name="Boletim">
        {() => <PlaceholderTab label="Boletim" />}
      </Tab.Screen>
      <Tab.Screen name="Financeiro">
        {() => <PlaceholderTab label="Financeiro" />}
      </Tab.Screen>
      <Tab.Screen name="Perfil">
        {() => <PlaceholderTab label="Perfil" />}
      </Tab.Screen>
    </Tab.Navigator>
  );
}
