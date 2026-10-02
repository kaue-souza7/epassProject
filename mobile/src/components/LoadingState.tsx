import { useEffect, useRef } from "react";
import { createThemedStyles } from "../theme/useThemedStyles";
import {
  View,
  ActivityIndicator,
  Animated,
  Easing,
  StyleSheet,
} from "react-native";

interface LoadingStateProps {
  color?: string;
  size?: "small" | "large";
  label?: string;
}

export function LoadingState({
  color = "#FF5B8F",
  size = "large",
  label = "Carregando",
}: LoadingStateProps) {
  const pulse = useRef(new Animated.Value(0)).current;
  const halo = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: 700,
          easing: Easing.inOut(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: 700,
          easing: Easing.inOut(Easing.cubic),
          useNativeDriver: true,
        }),
      ]),
    ).start();

    Animated.loop(
      Animated.timing(halo, {
        toValue: 1,
        duration: 1800,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ).start();
  }, [pulse, halo]);

  return (
    <View style={styles.container} accessibilityLabel={label} accessibilityRole="progressbar">
      <Animated.View
        style={[
          styles.halo,
          {
            backgroundColor: color,
            opacity: halo.interpolate({
              inputRange: [0, 0.4, 1],
              outputRange: [0.22, 0.12, 0],
            }),
            transform: [
              { scale: halo.interpolate({ inputRange: [0, 1], outputRange: [0.5, 1.7] }) },
            ],
          },
        ]}
      />
      <Animated.View
        style={{
          transform: [
            { scale: pulse.interpolate({ inputRange: [0, 1], outputRange: [0.9, 1.06] }) },
          ],
        }}
      >
        <ActivityIndicator size={size} color={color} />
      </Animated.View>
    </View>
  );
}

const styles = createThemedStyles({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 32,
  },
  halo: {
    position: "absolute",
    width: 72,
    height: 72,
    borderRadius: 36,
  },
});
