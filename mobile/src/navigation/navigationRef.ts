import { createNavigationContainerRef } from "@react-navigation/native";

export const navigationRef = createNavigationContainerRef<any>();

export interface NotificacaoPayload {
  entidade_tipo?: string | null;
  entidade_id?: string | null;
  aviso_id?: string | null;
  ocorrencia_id?: string | null;
}

/**
 * Deep link de notificação para o conteúdo correto.
 *
 * - Ocorrência → tela de detalhe da ocorrência.
 * - Aviso → aba de avisos com a conversa aberta.
 * - Sem identificador → aba de avisos (central).
 *
 * Só o perfil responsável possui essas telas no app; para outros perfis a
 * navegação é ignorada com segurança.
 */
export function abrirNotificacaoNoApp(payload: NotificacaoPayload): boolean {
  if (!navigationRef.isReady()) return false;

  const navigate = navigationRef.navigate as unknown as (
    ...args: unknown[]
  ) => void;

  const ocorrenciaId =
    payload.ocorrencia_id ??
    (payload.entidade_tipo === "ocorrencia" ? payload.entidade_id : null);
  const avisoId =
    payload.aviso_id ??
    (payload.entidade_tipo === "aviso" ? payload.entidade_id : null);

  try {
    if (ocorrenciaId) {
      navigate("Responsavel", {
        screen: "OcorrenciaDetalhe",
        params: { ocorrenciaId },
      });
      return true;
    }
    if (avisoId) {
      navigate("Responsavel", {
        screen: "HomeTabs",
        params: { screen: "Avisos", params: { avisoId } },
      });
      return true;
    }
    navigate("Responsavel", { screen: "HomeTabs", params: { screen: "Avisos" } });
    return true;
  } catch {
    return false;
  }
}
