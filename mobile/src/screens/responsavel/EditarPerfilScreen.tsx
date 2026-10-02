import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { ThemedIcon } from "../../theme/ThemedIcon";
import { useThemeVersion } from "../../theme/useThemeVersion";
import { createThemedStyles } from "../../theme/useThemedStyles";
import { ScreenHeader } from "../../components/ScreenHeader";
import { useToast } from "../../components/Toast";
import { useAuth } from "../../contexts/AuthContext";
import { getApiErrorMessage } from "../../api/errors";
import { changePassword, updateMe } from "../../api/profile.service";

type ModoSenha = "atual" | "nova" | "confirmar";

/** Limite aplicado pelo backend em `PATCH /auth/me`; acima disso a API rejeita. */
const MAX_NOME = 200;
const MAX_EMAIL = 254;
const MIN_SENHA = 8;
const MAX_SENHA = 72;

export function EditarPerfilScreen() {
  // Re-renderiza a tela quando a paleta/escala do tema muda.
  useThemeVersion();
  const navigation = useNavigation();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { user, applyUser, logout } = useAuth();

  const [nome, setNome] = useState(user?.nome ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [salvandoDados, setSalvandoDados] = useState(false);

  const [senhaVisivel, setSenhaVisivel] = useState(false);
  const [senhas, setSenhas] = useState<Record<ModoSenha, string>>({
    atual: "",
    nova: "",
    confirmar: "",
  });
  const [salvandoSenha, setSalvandoSenha] = useState(false);

  const nomeRef = useRef<TextInput>(null);
  const emailRef = useRef<TextInput>(null);
  const senhaAtualRef = useRef<TextInput>(null);
  const senhaNovaRef = useRef<TextInput>(null);
  const senhaConfirmarRef = useRef<TextInput>(null);

  // O usuário autenticado é a fonte da verdade do formulário. Se ele mudar
  // (conta editada em outro dispositivo, sessão restaurada), os campos ficariam
  // com o valor antigo e `dadosAlterados` compararia contra um `user.nome`
  // novo, habilitando "Salvar" sem nenhuma edição real.
  const nomeServidor = user?.nome ?? "";
  const emailServidor = user?.email ?? "";
  useEffect(() => {
    setNome(nomeServidor);
    setEmail(emailServidor);
  }, [nomeServidor, emailServidor]);

  const dadosAlterados =
    nome.trim() !== nomeServidor || email.trim() !== emailServidor;

  const aoSalvarDados = useCallback(async () => {
    if (salvandoDados) return;

    const nomeLimpo = nome.trim();
    if (nomeLimpo.length < 3) {
      toast.warning("Informe um nome com ao menos 3 caracteres.");
      return;
    }
    const emailLimpo = email.trim().toLowerCase();
    if (!emailLimpo.includes("@") || !emailLimpo.includes(".")) {
      toast.warning("Informe um e-mail válido.");
      return;
    }

    setSalvandoDados(true);
    try {
      const atualizado = await updateMe({
        nome: nomeLimpo,
        email: emailLimpo,
      });
      applyUser(atualizado);
      setNome(atualizado.nome);
      setEmail(atualizado.email);
      toast.success("Informações atualizadas.");
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Não foi possível salvar"));
    } finally {
      setSalvandoDados(false);
    }
  }, [applyUser, email, nome, salvandoDados, toast]);

  const aoTrocarSenha = useCallback(async () => {
    if (salvandoSenha) return;

    if (!senhas.atual || !senhas.nova || !senhas.confirmar) {
      toast.warning("Preencha todos os campos de senha.");
      return;
    }
    if (senhas.nova.length < MIN_SENHA) {
      toast.warning(
        `A nova senha deve ter ao menos ${MIN_SENHA} caracteres.`,
      );
      return;
    }
    if (senhas.nova !== senhas.confirmar) {
      toast.warning("A confirmação não confere com a nova senha.");
      return;
    }
    if (senhas.nova === senhas.atual) {
      toast.warning("A nova senha deve ser diferente da atual.");
      return;
    }

    setSalvandoSenha(true);
    try {
      await changePassword({
        senha_atual: senhas.atual,
        nova_senha: senhas.nova,
      });
      setSenhas({ atual: "", nova: "", confirmar: "" });
      setSenhaVisivel(false);
      // A troca revoga as sessões no servidor. Um Toast não serve aqui: o
      // logout desmonta a tela que o exibiria, então o aviso vai em diálogo.
      Alert.alert(
        "Senha alterada",
        "Por segurança, você foi desconectado. Entre novamente com a nova senha.",
        [
          {
            text: "Entrar novamente",
            onPress: () => {
              void logout();
            },
          },
        ],
        { cancelable: false },
      );
    } catch (err) {
      toast.error(getApiErrorMessage(err, "Não foi possível trocar a senha"));
    } finally {
      setSalvandoSenha(false);
    }
  }, [logout, salvandoSenha, senhas, toast]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScreenHeader title="Editar informações" subtitle="Seus dados de acesso" />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + 32 },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Dados pessoais</Text>

          <Text style={styles.label}>Nome completo</Text>
          <TextInput
            ref={nomeRef}
            style={styles.input}
            value={nome}
            onChangeText={setNome}
            placeholder="Seu nome"
            placeholderTextColor="#B0B0B0"
            autoCapitalize="words"
            autoCorrect={false}
            maxLength={MAX_NOME}
            returnKeyType="next"
            onSubmitEditing={() => emailRef.current?.focus()}
            textContentType="name"
            accessibilityLabel="Nome completo"
          />

          <Text style={styles.label}>E-mail</Text>
          <TextInput
            ref={emailRef}
            style={styles.input}
            value={email}
            onChangeText={setEmail}
            placeholder="seu@email.com"
            placeholderTextColor="#B0B0B0"
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            maxLength={MAX_EMAIL}
            returnKeyType="done"
            onSubmitEditing={() => {
              emailRef.current?.blur();
              void aoSalvarDados();
            }}
            textContentType="emailAddress"
            accessibilityLabel="E-mail"
          />

          <TouchableOpacity
            style={[styles.primaryButton, salvandoDados && styles.buttonDisabled]}
            onPress={aoSalvarDados}
            disabled={salvandoDados || !dadosAlterados}
            activeOpacity={0.8}
            accessibilityRole="button"
            accessibilityLabel="Salvar informações"
          >
            {salvandoDados ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <ThemedIcon name="checkmark" size={20} color="#FFFFFF" />
            )}
            <Text style={styles.primaryButtonText}>Salvar alterações</Text>
          </TouchableOpacity>

          {!dadosAlterados && (
            <Text style={styles.helper}>
              Faça uma alteração para habilitar o salvamento.
            </Text>
          )}
        </View>

        <View style={styles.card}>
          <View style={styles.rowBetween}>
            <Text style={styles.sectionTitle}>Senha</Text>
            <TouchableOpacity
              onPress={() => setSenhaVisivel((v) => !v)}
              accessibilityRole="button"
              accessibilityLabel={
                senhaVisivel ? "Ocultar alteração de senha" : "Alterar senha"
              }
            >
              <Text style={styles.linkAction}>
                {senhaVisivel ? "Cancelar" : "Alterar"}
              </Text>
            </TouchableOpacity>
          </View>

          {senhaVisivel ? (
            <View>
              <Text style={styles.label}>Senha atual</Text>
              <TextInput
                ref={senhaAtualRef}
                style={styles.input}
                value={senhas.atual}
                onChangeText={(t) => setSenhas((s) => ({ ...s, atual: t }))}
                placeholder="••••••••"
                placeholderTextColor="#B0B0B0"
                secureTextEntry
                autoCapitalize="none"
                maxLength={MAX_SENHA}
                returnKeyType="next"
                onSubmitEditing={() => senhaNovaRef.current?.focus()}
                textContentType="password"
                accessibilityLabel="Senha atual"
              />

              <Text style={styles.label}>Nova senha</Text>
              <TextInput
                ref={senhaNovaRef}
                style={styles.input}
                value={senhas.nova}
                onChangeText={(t) => setSenhas((s) => ({ ...s, nova: t }))}
                placeholder={`Mínimo de ${MIN_SENHA} caracteres`}
                placeholderTextColor="#B0B0B0"
                secureTextEntry
                autoCapitalize="none"
                maxLength={MAX_SENHA}
                returnKeyType="next"
                onSubmitEditing={() => senhaConfirmarRef.current?.focus()}
                textContentType="newPassword"
                accessibilityLabel="Nova senha"
              />

              <Text style={styles.label}>Confirmar nova senha</Text>
              <TextInput
                ref={senhaConfirmarRef}
                style={styles.input}
                value={senhas.confirmar}
                onChangeText={(t) => setSenhas((s) => ({ ...s, confirmar: t }))}
                placeholder="Repita a nova senha"
                placeholderTextColor="#B0B0B0"
                secureTextEntry
                autoCapitalize="none"
                maxLength={MAX_SENHA}
                returnKeyType="done"
                onSubmitEditing={() => {
                  senhaConfirmarRef.current?.blur();
                  void aoTrocarSenha();
                }}
                textContentType="newPassword"
                accessibilityLabel="Confirmar nova senha"
              />

              <View style={styles.warningBox}>
                <ThemedIcon
                  name="information-circle-outline"
                  size={18}
                  color="#B26A00"
                />
                <Text style={styles.warningText}>
                  Por segurança, você será desconectado de todos os
                  dispositivos após trocar a senha.
                </Text>
              </View>

              <TouchableOpacity
                style={[styles.primaryButton, salvandoSenha && styles.buttonDisabled]}
                onPress={aoTrocarSenha}
                disabled={salvandoSenha}
                activeOpacity={0.8}
                accessibilityRole="button"
                accessibilityLabel="Confirmar nova senha"
              >
                {salvandoSenha ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <ThemedIcon name="key" size={18} color="#FFFFFF" />
                )}
                <Text style={styles.primaryButtonText}>Salvar nova senha</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <Text style={styles.helper}>
              Use uma senha forte e diferente das que você já usa.
            </Text>
          )}
        </View>

        <TouchableOpacity
          style={styles.backLink}
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel="Voltar ao perfil"
        >
          <ThemedIcon name="arrow-back" size={18} color="#FF5B8F" />
          <Text style={styles.backLinkText}>Voltar</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = createThemedStyles({
  container: {
    flex: 1,
    backgroundColor: "#F5F5F7",
  },
  scroll: {
    flex: 1,
  },
  content: {
    paddingHorizontal: 24,
    paddingTop: 8,
    gap: 20,
  },
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
    marginBottom: 12,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#7A7A7A",
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    backgroundColor: "#F0F0F3",
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 15,
    color: "#1F1F1F",
    borderWidth: 1,
    borderColor: "#E5E5E5",
  },
  primaryButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    backgroundColor: "#FF5B8F",
    borderRadius: 16,
    paddingVertical: 15,
    marginTop: 20,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  primaryButtonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
  },
  helper: {
    fontSize: 13,
    color: "#7A7A7A",
    marginTop: 12,
    lineHeight: 18,
  },
  rowBetween: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  linkAction: {
    fontSize: 14,
    fontWeight: "600",
    color: "#FF5B8F",
  },
  warningBox: {
    flexDirection: "row",
    gap: 8,
    backgroundColor: "#FFF3D6",
    borderRadius: 12,
    padding: 12,
    marginTop: 16,
  },
  warningText: {
    flex: 1,
    fontSize: 12,
    color: "#B26A00",
    lineHeight: 17,
  },
  backLink: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 12,
  },
  backLinkText: {
    fontSize: 15,
    fontWeight: "600",
    color: "#FF5B8F",
  },
});
