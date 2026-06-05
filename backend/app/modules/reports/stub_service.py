from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.modules.reports.schemas import (
    BimestreEvolucao,
    ComprovantePagamento,
    DadosEvolucao,
    DeclaracaoMatricula,
    DisciplinaHistorico,
    DocumentoPdf,
    HistoricoEscolar,
    RelatorioFrequencia,
)
from app.shared.enums import SituacaoAluno


class RelatorioStubService:
    """Stub service that returns mock data for reports.

    TODO: Replace with real database queries when the actual reports
    module is fully implemented.
    """

    async def obter_relatorio_frequencia(
        self,
        enrollment_id: uuid.UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> RelatorioFrequencia:
        _ = enrollment_id
        hoje = date.today()
        inicio = start_date or date(hoje.year, 1, 1)
        fim = end_date or hoje
        return RelatorioFrequencia(
            matricula_id=enrollment_id,
            aluno_nome="João Silva",
            turma_codigo="3A",
            ano_letivo=hoje.year,
            periodo_inicio=inicio,
            periodo_fim=fim,
            total_aulas=120,
            presencas=108,
            faltas=8,
            faltas_justificadas=4,
            frequencia_media=90.0,
        )

    async def obter_historico_escolar(
        self, student_id: uuid.UUID,
    ) -> HistoricoEscolar:
        _ = student_id
        return HistoricoEscolar(
            aluno_id=student_id,
            aluno_nome="João Silva",
            disciplinas=[
                DisciplinaHistorico(
                    disciplina_nome="Matemática",
                    ano_letivo=2025,
                    serie_nome="3º Ano",
                    situacao=SituacaoAluno.APROVADO,
                    media_final=Decimal("8.5"),
                ),
                DisciplinaHistorico(
                    disciplina_nome="Português",
                    ano_letivo=2025,
                    serie_nome="3º Ano",
                    situacao=SituacaoAluno.APROVADO,
                    media_final=Decimal("7.8"),
                ),
                DisciplinaHistorico(
                    disciplina_nome="História",
                    ano_letivo=2024,
                    serie_nome="2º Ano",
                    situacao=SituacaoAluno.APROVADO,
                    media_final=Decimal("9.0"),
                ),
                DisciplinaHistorico(
                    disciplina_nome="Geografia",
                    ano_letivo=2024,
                    serie_nome="2º Ano",
                    situacao=SituacaoAluno.APROVADO,
                    media_final=Decimal("8.2"),
                ),
                DisciplinaHistorico(
                    disciplina_nome="Ciências",
                    ano_letivo=2023,
                    serie_nome="1º Ano",
                    situacao=SituacaoAluno.APROVADO,
                    media_final=Decimal("7.5"),
                ),
            ],
        )

    async def obter_declaracao_matricula(
        self, enrollment_id: uuid.UUID,
    ) -> DeclaracaoMatricula:
        return DeclaracaoMatricula(
            matricula_id=enrollment_id,
            aluno_nome="João Silva",
            turma_codigo="3A",
            serie_nome="3º Ano",
            ano_letivo=date.today().year,
            data_emissao=date.today(),
            situacao=SituacaoAluno.APROVADO,
        )

    async def obter_comprovante_pagamento(
        self, movement_id: uuid.UUID,
    ) -> ComprovantePagamento:
        return ComprovantePagamento(
            movimento_id=movement_id,
            descricao="Mensalidade Março/2025",
            valor=Decimal("450.00"),
            data_pagamento=date.today() - timedelta(days=5),
            forma_pagamento="PIX",
            aluno_nome="João Silva",
        )

    async def obter_dados_evolucao(
        self, enrollment_id: uuid.UUID,
    ) -> DadosEvolucao:
        return DadosEvolucao(
            matricula_id=enrollment_id,
            aluno_nome="João Silva",
            turma_codigo="3A",
            serie_nome="3º Ano",
            ano_letivo=date.today().year,
            bimestres=[
                BimestreEvolucao(bimestre=1, media_geral=7.5, frequencia=92.0),
                BimestreEvolucao(bimestre=2, media_geral=8.0, frequencia=88.0),
                BimestreEvolucao(bimestre=3, media_geral=7.8, frequencia=90.0),
                BimestreEvolucao(bimestre=4, media_geral=8.5, frequencia=91.0),
            ],
        )

    async def gerar_pdf(
        self, tipo: str, ids: dict[str, str],
    ) -> DocumentoPdf:
        _ = ids
        return DocumentoPdf(
            id=str(uuid.uuid4()),
            tipo=tipo,
            url=f"https://api.epass.app/reports/download/{tipo}/{uuid.uuid4()}",
            nome_arquivo=f"{tipo}_{date.today().isoformat()}.pdf",
        )
