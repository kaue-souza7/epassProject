import { api } from "./client";
import type { MeResponse } from "../types";

/** Atualiza nome e/ou e-mail do usuário logado. */
export async function updateMe(dados: {
  nome?: string;
  email?: string;
}): Promise<MeResponse> {
  const { data } = await api.patch<MeResponse>("/auth/me", dados);
  return data;
}

/** Troca a senha. Encerra as sessões ativas ao concluir. */
export async function changePassword(dados: {
  senha_atual: string;
  nova_senha: string;
}): Promise<void> {
  await api.post("/auth/me/senha", dados);
}
