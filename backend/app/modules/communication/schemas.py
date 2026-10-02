from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.shared.enums import (
    PrioridadeAviso,
    SeveridadeOcorrencia,
    StatusAviso,
    StatusOcorrencia,
    TipoAviso,
    TipoNotificacao,
    TipoOcorrencia,
)

# ── Ocorrências ────────────────────────────────────────────────────

class OcorrenciaCreate(BaseModel):
    aluno_id: uuid.UUID | None = None
    turma_id: uuid.UUID | None = None
    titulo: str = Field(..., min_length=3, max_length=200)
    descricao: str = Field(..., min_length=3)
    tipo: TipoOcorrencia = TipoOcorrencia.COMPORTAMENTO
    severidade: SeveridadeOcorrencia = SeveridadeOcorrencia.MEDIA
    responsavel_id: uuid.UUID | None = None


class OcorrenciaUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    descricao: str | None = Field(default=None, min_length=3)
    tipo: TipoOcorrencia | None = None
    severidade: SeveridadeOcorrencia | None = None
    responsavel_id: uuid.UUID | None = None


class OcorrenciaStatusUpdate(BaseModel):
    status: StatusOcorrencia
    observacao: str | None = Field(default=None, max_length=255)


class OcorrenciaHistoricoResponse(BaseModel):
    id: uuid.UUID
    status_anterior: StatusOcorrencia | None
    status_novo: StatusOcorrencia | None
    acao: str
    autor_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OcorrenciaResponse(BaseModel):
    id: uuid.UUID
    aluno_id: uuid.UUID | None
    aluno_nome: str | None = None
    turma_id: uuid.UUID | None
    turma_codigo: str | None = None
    titulo: str
    descricao: str
    tipo: TipoOcorrencia
    severidade: SeveridadeOcorrencia
    status: StatusOcorrencia
    criado_por: uuid.UUID
    responsavel_id: uuid.UUID | None
    resolvida_em: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OcorrenciaDetalheResponse(BaseModel):
    ocorrencia: OcorrenciaResponse
    historico: list[OcorrenciaHistoricoResponse] = []


# ── Avisos ─────────────────────────────────────────────────────────

class AvisoCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    mensagem: str = Field(..., min_length=3)
    tipo: TipoAviso = TipoAviso.GERAL
    prioridade: PrioridadeAviso = PrioridadeAviso.MEDIA
    permite_respostas: bool = False

    # Público-alvo (resolvido e validado no backend conforme o perfil)
    para_professores: bool = False
    professor_ids: list[uuid.UUID] = Field(default_factory=list)
    para_responsaveis: bool = False
    responsavel_ids: list[uuid.UUID] = Field(default_factory=list)
    turma_ids: list[uuid.UUID] = Field(default_factory=list)

    # Compatibilidade com o fluxo anterior (aluno/turma únicos)
    destinatario_aluno_id: uuid.UUID | None = None
    destinatario_turma_id: uuid.UUID | None = None


class AvisoUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=200)
    mensagem: str | None = Field(default=None, min_length=3)
    tipo: TipoAviso | None = None
    prioridade: PrioridadeAviso | None = None
    permite_respostas: bool | None = None
    status: StatusAviso | None = None
    # Re-sincronização de público (apenas adiciona novos destinatários)
    para_professores: bool | None = None
    professor_ids: list[uuid.UUID] | None = None
    para_responsaveis: bool | None = None
    responsavel_ids: list[uuid.UUID] | None = None
    turma_ids: list[uuid.UUID] | None = None


class AusenciaCreate(BaseModel):
    """Aviso de "meu filho não vem hoje", disparado pelo botão do responsável."""

    aluno_id: uuid.UUID
    data: date | None = Field(
        default=None,
        description="Dia da ausência. Padrão: hoje. Aceitar o dia permite avisar com "
        "antecedência (ex.: o filho faltar segunda e avisar na sexta).",
    )
    motivo: str | None = Field(
        default=None, max_length=500, description="Motivo informado pelo responsável",
    )


class AusenciaResponse(BaseModel):
    """O que foi criado e quem ficou sabendo — o responsável precisa ver o efeito,
    não só um 201, para saber se avisou a pessoa certa."""

    aviso_id: uuid.UUID
    aluno_id: uuid.UUID
    aluno_nome: str | None = None
    data: date
    turma_codigo: str | None = None
    turno: str | None = None
    # Secretarias e professores notificados, para a tela mostrar quem recebeu.
    secretaria: int = 0
    professores: int = 0
    professores_nomes: list[str] = Field(default_factory=list)
    # Verdadeiro quando não havia grade cadastrada para o dia e o aviso foi então
    # endereçado só à secretaria. A secretaria precisa saber para pedir ao professor
    # que cadastre a grade.
    sem_grade: bool = False
    ja_existia: bool = False


class AvisoDestinatarioResponse(BaseModel):
    id: uuid.UUID
    aviso_id: uuid.UUID
    usuario_id: uuid.UUID
    usuario_nome: str | None = None
    usuario_perfil: str | None = None
    aluno_id: uuid.UUID | None = None
    aluno_nome: str | None = None
    lido_em: datetime | None
    escalado_em: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AvisoEstatisticasResponse(BaseModel):
    total: int = 0
    lidos: int = 0
    nao_lidos: int = 0


class AvisoResponse(BaseModel):
    id: uuid.UUID
    titulo: str
    mensagem: str
    tipo: TipoAviso
    prioridade: PrioridadeAviso
    permite_respostas: bool = False
    destinatario_aluno_id: uuid.UUID | None
    destinatario_turma_id: uuid.UUID | None
    status: StatusAviso
    criado_por: uuid.UUID
    autor_nome: str | None = None
    autor_perfil: str | None = None
    publicado_em: datetime
    created_at: datetime
    lido_por_mim: bool = False
    sou_autor: bool = False
    total_destinatarios: int = 0
    lidos: int = 0
    nao_lidos: int = 0

    model_config = {"from_attributes": True}


class AvisoMensagemCreate(BaseModel):
    conteudo: str = Field(..., min_length=1, max_length=4000)
    destinatario_id: uuid.UUID | None = None


class AvisoMensagemResponse(BaseModel):
    id: uuid.UUID
    aviso_id: uuid.UUID
    autor_id: uuid.UUID
    autor_nome: str | None = None
    autor_perfil: str | None = None
    destinatario_id: uuid.UUID
    destinatario_nome: str | None = None
    conteudo: str
    lida_em: datetime | None
    created_at: datetime
    enviada_por_mim: bool = False

    model_config = {"from_attributes": True}


class AvisoDetalheResponse(BaseModel):
    aviso: AvisoResponse
    destinatarios: list[AvisoDestinatarioResponse] = Field(default_factory=list)
    estatisticas: AvisoEstatisticasResponse = Field(default_factory=AvisoEstatisticasResponse)
    pode_responder: bool = False
    total_mensagens: int = 0


# ── Público disponível para envio ──────────────────────────────────

class PublicoPessoaResponse(BaseModel):
    id: uuid.UUID
    nome: str
    aluno_id: uuid.UUID | None = None
    aluno_nome: str | None = None
    turma_codigo: str | None = None


class PublicoTurmaResponse(BaseModel):
    id: uuid.UUID
    codigo: str
    nome: str | None = None


class PublicoDisponivelResponse(BaseModel):
    professores: list[PublicoPessoaResponse] = []
    responsaveis: list[PublicoPessoaResponse] = []
    turmas: list[PublicoTurmaResponse] = []
    pode_enviar_para_professores: bool = False
    pode_enviar_para_todos_responsaveis: bool = False


# ── Notificações ───────────────────────────────────────────────────

class NotificacaoResponse(BaseModel):
    id: uuid.UUID
    destinatario_id: uuid.UUID
    tipo: TipoNotificacao
    titulo: str
    mensagem: str
    canal: str
    entidade_tipo: str | None
    entidade_id: uuid.UUID | None
    dados: dict | None
    lida: bool
    lida_em: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificacaoNaoLidasResponse(BaseModel):
    total: int


class PushTokenRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=255)
    plataforma: str = Field(default="expo", max_length=20)


class PushTokenResponse(BaseModel):
    id: uuid.UUID
    token: str
    plataforma: str
    ativo: bool

    model_config = {"from_attributes": True}


class PreferenciaNotificacaoResponse(BaseModel):
    tipo: TipoNotificacao
    email: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class PreferenciaNotificacaoUpdate(BaseModel):
    email: bool


class PreferenciaNotificacaoListResponse(BaseModel):
    """Preferências do usuário, sempre com todos os tipos conhecidos.

    Tipos sem linha são devolvidos com `email: false`, para o app não precisar
    inferir o padrão a partir da ausência de chaves.
    """

    preferencias: dict[TipoNotificacao, bool]
