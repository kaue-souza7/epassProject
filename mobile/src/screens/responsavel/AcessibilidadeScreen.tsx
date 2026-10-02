import { useState } from "react";
import {
  ScrollView,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { ThemedIcon } from "../../theme/ThemedIcon";
import { FONT_SCALES } from "../../theme/tokens";
import { useTheme } from "../../contexts/ThemeContext";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { ScreenHeader } from "../../components/ScreenHeader";
import { KeepAwake } from "../../components/KeepAwake";
import { useToast } from "../../components/Toast";

export function AcessibilidadeScreen() {
  useThemeVersion();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const {
    isDark,
    setTheme,
    fontScale,
    fontScaleId,
    setFontScaleId,
    highContrast,
    setHighContrast,
    keepAwake,
    setKeepAwake,
  } = useTheme();

  const [preview, setPreview] = useState("Boletim do 2º bimestre");

  return (
    <View style={styles.container}>
      {/* Feedback imediato da preferência dentro da própria tela de ajuste. */}
      <KeepAwake />
      <ScreenHeader
        title="Acessibilidade"
        subtitle="Ajuste a leitura e a visibilidade"
      />

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + 32 },
        ]}
      >
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Tamanho do texto</Text>
          <Text style={styles.sectionHint}>
            Afeta todos os textos do aplicativo.
          </Text>

          <View style={styles.fontOptions}>
            {FONT_SCALES.map((opcao) => {
              const ativo = fontScaleId === opcao.id;
              return (
                <TouchableOpacity
                  key={opcao.id}
                  style={[
                    styles.fontOption,
                    ativo && styles.fontOptionAtivo,
                  ]}
                  onPress={() => setFontScaleId(opcao.id)}
                  activeOpacity={0.8}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: ativo }}
                  accessibilityLabel={`Tamanho de texto ${opcao.label}`}
                >
                  <Text
                    style={[
                      styles.fontPreview,
                      // A prévia precisa refletir a escala que o app está
                      // aplicando agora; um `fontSize` inline não passa pelo
                      // `createThemedStyles`, que é quem multiplica a escala.
                      { fontSize: Math.round(opcao.scale * 17 * fontScale) },
                      ativo && styles.fontPreviewAtivo,
                    ]}
                  >
                    Aa
                  </Text>
                  <Text
                    style={[
                      styles.fontLabel,
                      ativo && styles.fontLabelAtivo,
                    ]}
                  >
                    {opcao.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <View style={styles.previewBox}>
            <Text style={styles.previewLabel}>Prévia</Text>
            <Text style={styles.previewTexto}>{preview}</Text>
            <TextInput
              style={styles.previewInput}
              value={preview}
              onChangeText={setPreview}
              placeholder="Digite para testar"
              placeholderTextColor="#B0B0B0"
              accessibilityLabel="Campo de teste de texto"
            />
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Contraste</Text>
          <Text style={styles.sectionHint}>
            Aumenta a diferença entre textos e fundos.
          </Text>

          <OptionRow
            icon="contrast-outline"
            title="Alto contraste"
            description="Cores mais fortes para facilitar a leitura"
            value={highContrast}
            onChange={setHighContrast}
          />
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Tela</Text>

          <OptionRow
            icon="sunny-outline"
            title="Modo escuro"
            description="Fundo escuro para enxergar melhor à noite"
            value={isDark}
            onChange={(v) => setTheme(v ? "dark" : "light")}
          />

          <View style={styles.divider} />

          <OptionRow
            icon="phone-portrait-outline"
            title="Manter tela ligada"
            description="Não apaga a tela enquanto você lê boletins, avisos e documentos"
            value={keepAwake}
            onChange={setKeepAwake}
          />
        </View>

        <TouchableOpacity
          style={styles.restaurar}
          onPress={() => {
            setFontScaleId("padrao");
            setHighContrast(false);
            setKeepAwake(false);
            setTheme("light");
            toast.info("Ajustes restaurados para o padrão.");
          }}
          activeOpacity={0.8}
          accessibilityRole="button"
          accessibilityLabel="Restaurar ajustes padrão"
        >
          <ThemedIcon name="refresh-outline" size={18} color="#FF5B8F" />
          <Text style={styles.restaurarTexto}>Restaurar padrões</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

function OptionRow({
  icon,
  title,
  description,
  value,
  onChange,
}: {
  icon: string;
  title: string;
  description: string;
  value: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <View style={styles.optionRow}>
      <View style={styles.optionIcon}>
        <ThemedIcon name={icon as never} size={20} color="#FF5B8F" />
      </View>
      <View style={styles.optionInfo}>
        <Text style={styles.optionTitle}>{title}</Text>
        <Text style={styles.optionDescription}>{description}</Text>
      </View>
      <Switch
        value={value}
        onValueChange={onChange}
        trackColor={{ false: "#E5E5E5", true: "#FF5B8F" }}
        thumbColor="#FFFFFF"
        ios_backgroundColor="#E5E5E5"
        accessibilityLabel={title}
        accessibilityRole="switch"
      />
    </View>
  );
}

const styles = createThemedStyles({
  container: { flex: 1, backgroundColor: "#F5F5F7" },
  scroll: { flex: 1 },
  content: { paddingHorizontal: 24, paddingTop: 8, gap: 20 },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 24,
    padding: 20,
    borderWidth: 1,
    borderColor: "#E5E5E5",
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: "#1F1F1F",
  },
  sectionHint: {
    fontSize: 13,
    color: "#7A7A7A",
    marginTop: 4,
    marginBottom: 14,
  },
  fontOptions: { flexDirection: "row", gap: 8 },
  fontOption: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: "#F5F5F7",
    borderWidth: 1,
    borderColor: "#E5E5E5",
    gap: 4,
  },
  fontOptionAtivo: { backgroundColor: "#FFEAF1", borderColor: "#FF5B8F" },
  fontPreview: { fontWeight: "700", color: "#7A7A7A" },
  fontPreviewAtivo: { color: "#FF5B8F" },
  fontLabel: { fontSize: 11, color: "#7A7A7A" },
  fontLabelAtivo: { color: "#FF5B8F", fontWeight: "700" },
  previewBox: {
    marginTop: 16,
    backgroundColor: "#F5F5F7",
    borderRadius: 16,
    padding: 14,
    gap: 8,
    borderWidth: 1,
    borderColor: "#E5E5E5",
  },
  previewLabel: {
    fontSize: 11,
    fontWeight: "700",
    color: "#7A7A7A",
    textTransform: "uppercase",
  },
  previewTexto: { fontSize: 15, color: "#1F1F1F", lineHeight: 21 },
  previewInput: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: "#1F1F1F",
    borderWidth: 1,
    borderColor: "#E5E5E5",
  },
  optionRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  optionIcon: {
    width: 40,
    height: 40,
    borderRadius: 14,
    backgroundColor: "#FFEAF1",
    alignItems: "center",
    justifyContent: "center",
  },
  optionInfo: { flex: 1 },
  optionTitle: { fontSize: 15, fontWeight: "600", color: "#1F1F1F" },
  optionDescription: {
    fontSize: 12,
    color: "#7A7A7A",
    marginTop: 2,
    lineHeight: 16,
  },
  divider: {
    height: 1,
    backgroundColor: "#F0F0F3",
    marginVertical: 16,
  },
  restaurar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 14,
  },
  restaurarTexto: {
    fontSize: 14,
    fontWeight: "600",
    color: "#FF5B8F",
  },
});
