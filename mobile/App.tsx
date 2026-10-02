import { useEffect, useRef } from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { ActivityIndicator, Animated, Easing, View, StyleSheet } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AuthProvider, useAuth } from "./src/contexts/AuthContext";
import { ThemeProvider } from "./src/contexts/ThemeContext";
import { SelectedStudentProvider } from "./src/contexts/SelectedStudentContext";
import { NotificationsProvider } from "./src/contexts/NotificationsContext";
import { ToastProvider } from "./src/components/Toast";
import { RootNavigator } from "./src/navigation/RootNavigator";
import { navigationRef } from "./src/navigation/navigationRef";
import { createThemedStyles } from "./src/theme/useThemedStyles";

function SplashScreen() {
  const pulse = useRef(new Animated.Value(0)).current;
  const glow = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 900,
          easing: Easing.inOut(Easing.cubic),
          useNativeDriver: true,
        }),
      ]),
    ).start();

    Animated.loop(
      Animated.timing(glow, {
        toValue: 1,
        duration: 2200,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ).start();
  }, [pulse, glow]);

  return (
    <LinearGradient
      colors={["#FF5B8F", "#F43F6E", "#E84A7A"]}
      style={styles.loading}
    >
      <Animated.View
        style={[
          styles.splashGlow,
          {
            opacity: glow.interpolate({ inputRange: [0, 1], outputRange: [0.25, 0.6] }),
            transform: [
              { scale: glow.interpolate({ inputRange: [0, 1], outputRange: [0.7, 1.25] }) },
            ],
          },
        ]}
      />

      <Animated.View
        style={[
          styles.splashLogo,
          {
            transform: [
              { scale: pulse.interpolate({ inputRange: [0, 1], outputRange: [0.94, 1.06] }) },
            ],
          },
        ]}
      >
        <Animated.Image
          source={require("./assets/logo.png")}
          style={styles.splashImage}
          resizeMode="contain"
        />
      </Animated.View>

      <ActivityIndicator size="large" color="white" style={styles.splashSpinner} />
    </LinearGradient>
  );
}

function AppContent() {
  const { isLoading } = useAuth();

  if (isLoading) return <SplashScreen />;

  return (
    <SelectedStudentProvider>
      <NotificationsProvider>
        <NavigationContainer ref={navigationRef}>
          <RootNavigator />
          <StatusBar style="auto" />
        </NavigationContainer>
      </NotificationsProvider>
    </SelectedStudentProvider>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <SafeAreaProvider>
          <ToastProvider>
            <AppContent />
          </ToastProvider>
        </SafeAreaProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

const styles = createThemedStyles({
  loading: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#FF5B8F",
  },
  splashGlow: {
    position: "absolute",
    width: 320,
    height: 320,
    borderRadius: 160,
    backgroundColor: "#FFFFFF",
  },
  splashLogo: {
    width: 128,
    height: 128,
    alignItems: "center",
    justifyContent: "center",
  },
  splashImage: {
    width: 120,
    height: 120,
  },
  splashSpinner: {
    marginTop: 28,
  },
});
