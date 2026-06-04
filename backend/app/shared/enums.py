from enum import StrEnum


class Perfil(StrEnum):
    ADMIN = "admin"
    SECRETARIA = "secretaria"
    PROFESSOR = "professor"
    RESPONSAVEL = "responsavel"


class StatusMatricula(StrEnum):
    ATIVA = "ativa"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class StatusDocumento(StrEnum):
    PENDENTE = "pendente"
    EM_ANALISE = "em_analise"
    PRONTO = "pronto"
    ENTREGUE = "entregue"


class StatusAtividade(StrEnum):
    RASCUNHO = "rascunho"
    ABERTA = "aberta"
    FECHADA = "fechada"
    PUBLICADA = "publicada"


class StatusAula(StrEnum):
    AGENDADA = "agendada"
    REALIZADA = "realizada"
    CANCELADA = "cancelada"


class TipoAtividade(StrEnum):
    PROVA = "prova"
    TRABALHO = "trabalho"
    EXERCICIO = "exercicio"
    PROJETO = "projeto"
    PARTICIPACAO = "participacao"


class TipoDocumento(StrEnum):
    CARTEIRA_ESCOLAR = "carteira_escolar"
    ATESTADO_MATRICULA = "atestado_matricula"
    HISTORICO = "historico"
    DECLARACAO_TRANSFERENCIA = "declaracao_transferencia"
    BOLETIM = "boletim"


class TipoSanguineo(StrEnum):
    A_POSITIVO = "A+"
    A_NEGATIVO = "A-"
    B_POSITIVO = "B+"
    B_NEGATIVO = "B-"
    AB_POSITIVO = "AB+"
    AB_NEGATIVO = "AB-"
    O_POSITIVO = "O+"
    O_NEGATIVO = "O-"


class Turno(StrEnum):
    MANHA = "manha"
    TARDE = "tarde"
    INTEGRAL = "integral"


class DiaSemana(StrEnum):
    SEG = "seg"
    TER = "ter"
    QUA = "qua"
    QUI = "qui"
    SEX = "sex"
    SAB = "sab"


class StatusPagamento(StrEnum):
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    EXPIRADO = "expirado"
    CANCELADO = "cancelado"


class TipoTransacao(StrEnum):
    ENTRADA = "entrada"
    SAIDA = "saida"
    ESTORNO = "estorno"


class PrioridadeAviso(StrEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class TipoAviso(StrEnum):
    GERAL = "geral"
    COMPORTAMENTO = "comportamento"
    SAUDE = "saude"
    ADMINISTRATIVO = "administrativo"


class StatusJustificativa(StrEnum):
    PENDENTE = "pendente"
    APROVADA = "aprovada"
    REJEITADA = "rejeitada"


class Parentesco(StrEnum):
    PAI = "pai"
    MAE = "mae"
    AVO = "avo"
    AVA = "ava"
    TIO = "tio"
    TIA = "tia"
    IRMAO = "irmao"
    IRMA = "irma"
    TUTOR = "tutor"
    OUTRO = "outro"


class StatusFrequencia(StrEnum):
    PRESENTE = "presente"
    FALTA = "falta"
    FALTA_JUSTIFICADA = "falta_justificada"


class TipoAvaliacao(StrEnum):
    PROVA = "prova"
    TRABALHO = "trabalho"
    ATIVIDADE = "atividade"
    RECUPERACAO = "recuperacao"
    SIMULADO = "simulado"
    OUTRO = "outro"


class SituacaoAluno(StrEnum):
    APROVADO = "aprovado"
    REPROVADO = "reprovado"
    RECUPERACAO = "recuperacao"
    APROVADO_POS_RECUPERACAO = "aprovado_pos_recuperacao"
    REPROVADO_POS_RECUPERACAO = "reprovado_pos_recuperacao"


class TipoDestinoEvento(StrEnum):
    PROFESSOR = "professor"
    RESPONSAVEL = "responsavel"
    TURMA = "turma"


class StatusPulseira(StrEnum):
    ATIVA = "ativa"
    BLOQUEADA = "bloqueada"
    CANCELADA = "cancelada"


class StatusCarteira(StrEnum):
    ATIVA = "ativa"
    BLOQUEADA = "bloqueada"
    CANCELADA = "cancelada"


class TipoMovimentacao(StrEnum):
    RECARGA = "recarga"
    CONSUMO = "consumo"
    ESTORNO = "estorno"
