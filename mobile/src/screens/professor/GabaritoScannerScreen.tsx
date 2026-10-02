import { useState, useRef, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { ProfessorStackParamList } from "../../types/navigation";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { ThemedIcon } from "../../theme/ThemedIcon";

type NavProp = NativeStackNavigationProp<ProfessorStackParamList>;
type ScreenRoute = RouteProp<ProfessorStackParamList, "GabaritoScanner">;

export function GabaritoScannerScreen() {
  useThemeVersion();

  const navigation = useNavigation<NavProp>();
  const route = useRoute<ScreenRoute>();
  const { avaliacaoId, avaliacaoTitulo, notaMaxima, alocacaoId, turmaId, turmaNome, disciplinaNome } = route.params;

  const [permission, requestPermission] = useCameraPermissions();
  const [capturing, setCapturing] = useState(false);
  const cameraRef = useRef<CameraView>(null);

  const handleCapture = useCallback(async () => {
    if (!cameraRef.current) return;
    setCapturing(true);
    try {
      await cameraRef.current.takePictureAsync();

      navigation.navigate("GabaritoProcessamento", {
        avaliacaoId,
        avaliacaoTitulo,
        notaMaxima,
        alocacaoId,
        turmaId,
        turmaNome,
        disciplinaNome,
      });
    } catch {
      setCapturing(false);
    }
  }, [cameraRef, avaliacaoId, navigation, avaliacaoTitulo, notaMaxima, alocacaoId, turmaId, turmaNome, disciplinaNome]);

  if (!permission) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <ScreenHeader title="Escanear Folha" />
          <View style={styles.center}>
            <ActivityIndicator size="large" color="#6C63FF" />
          </View>
        </SafeAreaView>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <SafeAreaView style={styles.safeArea}>
          <ScreenHeader title="Escanear Folha" />
          <View style={styles.center}>
            <ThemedIcon name="camera-outline" size={64} color="#D0D0D0" />
            <Text style={styles.permissionTitle}>Permissão necessária</Text>
            <Text style={styles.permissionText}>
              O ePass precisa acessar a câmera para escanear a folha de respostas.
            </Text>
            <TouchableOpacity
              style={styles.permissionButton}
              onPress={requestPermission}
              accessibilityLabel="Permitir acesso à câmera"
              accessibilityRole="button"
            >
              <Text style={styles.permissionButtonText}>Permitir Câmera</Text>
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScreenHeader title="Escanear Folha" />
      </SafeAreaView>

      <CameraView
        ref={cameraRef}
        style={styles.camera}
        facing="back"
        flash="auto"
        ratio="4:3"
      >
        <View style={styles.viewfinder}>
          <View style={styles.viewfinderFrame}>
            <View style={styles.viewfinderCorner} />
            <View style={[styles.viewfinderCorner, styles.cornerTR]} />
            <View style={[styles.viewfinderCorner, styles.cornerBL]} />
            <View style={[styles.viewfinderCorner, styles.cornerBR]} />
          </View>
          <Text style={styles.viewfinderText}>
            Posicione a folha dentro da área
          </Text>
        </View>

        <View style={styles.cameraFooter}>
          <TouchableOpacity
            style={styles.captureButton}
            onPress={handleCapture}
            disabled={capturing}
            accessibilityLabel="Fotografar folha de respostas"
            accessibilityRole="button"
          >
            {capturing ? (
              <ActivityIndicator size="small" color="#FFF" />
            ) : (
              <View style={styles.captureInner} />
            )}
          </TouchableOpacity>
        </View>
      </CameraView>
    </View>
  );
}

const styles = createThemedStyles({
  container: {
    flex: 1,
    backgroundColor: "#000",
  },
  safeArea: {
    backgroundColor: "rgba(0,0,0,0.3)",
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
    backgroundColor: "#F5F5F7",
  },
  camera: {
    flex: 1,
  },
  viewfinder: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 40,
  },
  viewfinderFrame: {
    width: "80%",
    aspectRatio: 0.7,
    borderWidth: 0,
    position: "relative",
  },
  viewfinderCorner: {
    position: "absolute",
    width: 30,
    height: 30,
    borderColor: "#6C63FF",
    top: 0,
    left: 0,
    borderTopWidth: 3,
    borderLeftWidth: 3,
  },
  cornerTR: {
    left: undefined,
    right: 0,
    borderLeftWidth: 0,
    borderRightWidth: 3,
  },
  cornerBL: {
    top: undefined,
    bottom: 0,
    borderTopWidth: 0,
    borderBottomWidth: 3,
  },
  cornerBR: {
    top: undefined,
    left: undefined,
    right: 0,
    bottom: 0,
    borderTopWidth: 0,
    borderLeftWidth: 0,
    borderRightWidth: 3,
    borderBottomWidth: 3,
  },
  viewfinderText: {
    color: "rgba(255,255,255,0.7)",
    fontSize: 14,
    marginTop: 24,
    textAlign: "center",
  },
  cameraFooter: {
    position: "absolute",
    bottom: 48,
    left: 0,
    right: 0,
    alignItems: "center",
  },
  captureButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "rgba(255,255,255,0.3)",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 4,
    borderColor: "#FFF",
  },
  captureInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: "#FFF",
  },
  permissionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#1F1F1F",
    marginTop: 16,
    marginBottom: 8,
  },
  permissionText: {
    fontSize: 14,
    color: "#888",
    textAlign: "center",
    lineHeight: 20,
    marginBottom: 24,
  },
  permissionButton: {
    backgroundColor: "#6C63FF",
    borderRadius: 28,
    paddingHorizontal: 32,
    paddingVertical: 14,
  },
  permissionButtonText: {
    fontSize: 16,
    fontWeight: "700",
    color: "#FFF",
  },
});
