import logging

from app.core.exceptions import AppException
from app.modules.ai import mensagens as textos

logger = logging.getLogger(__name__)


class AIException(AppException):
    """Base das falhas do módulo de IA.

    Regra da arquitetura: NENHUMA falha de IA pode derrubar o SGE. Estas
    exceções traduzem "a IA não conseguiu responder" em respostas HTTP limpias,
    enquanto os endpoints do SGE seguem funcionando normalmente.

    Os textos que o usuário lê NÃO são escritos aqui: vivem em
    `textos.py`, num catálogo único, e a barreira anti-vazamento é
    aplicada no router antes de qualquer resposta sair do backend.
    """


class IADisponivelErro(AIException):
    """Ollama inacessível (container parado, timeout de conexão, 5xx)."""

    def __init__(self, message: str = textos.IA_INDISPONIVEL):
        super().__init__(message=message, status_code=503, code="ia_indisponivel")


class ModeloNaoEncontradoErro(AIException):
    """O modelo configurado não está instalado no Ollama.

    O `modelo` entra no log, nunca na resposta: dizer qual modelo falta
    transformaria um detalhe de infraestrutura em texto de tela.
    """

    def __init__(self, modelo: str):
        logger.warning("AI: modelo configurado ausente: %s", modelo)
        super().__init__(
            message=textos.MODELO_NAO_DISPONIVEL,
            status_code=503,
            code="modelo_nao_disponivel",
        )


class LimiteConcorrenciaErro(AIException):
    """Já existe uma inferência em andamento e a fila está cheia."""

    def __init__(self, message: str = textos.IA_SOBRECARREGADA):
        super().__init__(message=message, status_code=429, code="ia_sobrecarregada")


class ContextoVazioErro(AIException):
    """Não há dados autorizados suficientes para responder à pergunta."""

    def __init__(self, message: str = textos.SEM_DADOS):
        super().__init__(message=message, status_code=200, code="sem_dados")


class IntencaoNaoReconhecidaErro(AIException):
    """A pergunta não corresponde a nenhuma intenção permitida ao perfil."""

    def __init__(self, message: str = textos.INTENCAO_NAO_RECONHECIDA):
        super().__init__(message=message, status_code=200, code="intencao_nao_reconhecida")


class IntencaoNaoPermitidaErro(AIException):
    """A intenção existe, mas não está na allowlist do perfil do usuário.

    A allowlist é aplicada ANTES da classificação: um responsável nem chega a
    tentar mapear uma pergunta administrativa. Nunca revelar ao usuário quais
    intenções existem para outros perfis.
    """

    def __init__(self, message: str = textos.INTENCAO_NAO_PERMITIDA):
        super().__init__(message=message, status_code=403, code="intencao_nao_permitida")


class EscopoNaoResolvidoErro(AIException):
    """A referência (aluno/turma) não pertence ao escopo do usuário.

    Detectado ANTES de qualquer consulta — o modelo de dados só é consultado com
    identificadores já resolvidos dentro do escopo.
    """

    def __init__(self, message: str = textos.ESCOPO_NAO_RESOLVIDO):
        super().__init__(message=message, status_code=200, code="escopo_nao_resolvido")
