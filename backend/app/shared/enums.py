from enum import StrEnum


class Perfil(StrEnum):
    ADMIN = "admin"
    SECRETARIA = "secretaria"
    COORDENADOR = "coordenador"
    PROFESSOR = "professor"
    RESPONSAVEL = "responsavel"
    CANTINEIRO = "cantineiro"


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
    # Aviso gerado pelo botão "não vir hoje" do responsável. É um tipo próprio
    # porque tem regra de destinatário diferente dos demais: secretaria +
    # professores da turma no dia, e não o público escolhido no compositor.
    AUSENCIA = "ausencia"


class OrdemAviso(StrEnum):
    """Critérios aceitos de ordenação da listagem de avisos."""

    RECENTES = "recentes"
    ANTIGOS = "antigos"
    PRIORIDADE = "prioridade"
    LIDOS = "lidos"


class LeituraAviso(StrEnum):
    """Recorte de leitura do usuário corrente sobre a listagem."""

    TODOS = "todos"
    NAO_LIDOS = "nao_lidos"
    LIDOS = "lidos"


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


class StatusPedido(StrEnum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    EM_PRODUCAO = "em_producao"
    PRONTO = "pronto"
    RETIRADO = "retirado"
    CANCELADO = "cancelado"


class OrigemPedido(StrEnum):
    RESPONSAVEL = "responsavel"
    PROGRAMACAO = "programacao"
    CONSUMO_DIRETO = "consumo_direto"


class TipoProgramacao(StrEnum):
    DIARIA = "diaria"
    GERAL = "geral"


class StatusProduto(StrEnum):
    ATIVO = "ativo"
    INATIVO = "inativo"


class CategoriaProduto(StrEnum):
    SALGADO = "SALGADO"
    LANCHE_QUENTE = "LANCHE_QUENTE"
    LANCHE_NATURAL = "LANCHE_NATURAL"
    DOCE = "DOCE"
    BOMBONIERE = "BOMBONIERE"


class TipoMovimentacaoEstoque(StrEnum):
    ENTRADA = "entrada"
    SAIDA = "saida"
    AJUSTE = "ajuste"


class TipoOcorrencia(StrEnum):
    COMPORTAMENTO = "comportamento"
    SAUDE = "saude"
    ACADEMICO = "academico"
    OUTRO = "outro"


class StatusOcorrencia(StrEnum):
    ABERTA = "aberta"
    EM_ANDAMENTO = "em_andamento"
    RESOLVIDA = "resolvida"
    ARQUIVADA = "arquivada"


class SeveridadeOcorrencia(StrEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class StatusAviso(StrEnum):
    PUBLICADO = "publicado"
    ARQUIVADO = "arquivado"


class TipoNotificacao(StrEnum):
    SISTEMA = "sistema"
    CANTINA = "cantina"
    BOLETIM = "boletim"
    OCORRENCIA = "ocorrencia"
    AVISO = "aviso"
    AGENDA = "agenda"
    FINANCEIRO = "financeiro"
    NOTA = "nota"
    FREQUENCIA = "frequencia"


class PapelMensagemIA(StrEnum):
    """Quem falou na conversa da Atena."""

    USUARIO = "usuario"
    ASSISTENTE = "assistente"


class TipoDocumento(StrEnum):
    """Documentos que um responsável pode solicitar à secretaria."""

    BOLETIM_BIMESTRAL = "boletim_bimestral"
    BOLETIM_ANUAL = "boletim_anual"
    HISTORICO_ESCOLAR = "historico_escolar"
    DECLARACAO_MATRICULA = "declaracao_matricula"
    COMPROVANTE_MATRICULA = "comprovante_matricula"
    COMPROVANTE_FREQUENCIA = "comprovante_frequencia"
    COMPROVANTE_ENDERECO = "comprovante_endereco"
    COMPROVANTE_RENDA = "comprovante_renda"
    OUTRO = "outro"


class StatusSolicitacaoDocumento(StrEnum):
    PENDENTE = "pendente"
    EM_ANALISE = "em_analise"
    CONCLUIDA = "concluida"
    RECUSADA = "recusada"
    CANCELADA = "cancelada"
