export type TipoAutorizacao = "temporaria" | "diaria";

export interface AutorizacaoMock {
  id: string;
  aluno_id: string;
  aluno_nome: string;
  turma_codigo: string;
  nome_autorizado: string;
  cpf: string;
  tipo: TipoAutorizacao;
  created_at: string;
  expires_at: string;
  status: "ativa" | "cancelada" | "expirada";
}
