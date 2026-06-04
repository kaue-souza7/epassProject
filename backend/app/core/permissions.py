from typing import Literal

Perfil = Literal["admin", "secretaria", "professor", "responsavel"]

REGISTRY: dict[Perfil, list[tuple[str, str, str]]] = {
    "admin": [("*", "*", "*")],
    "secretaria": [
        ("aluno", "create", "all"),
        ("aluno", "read", "all"),
        ("aluno", "update", "all"),
        ("matricula", "create", "all"),
        ("matricula", "read", "all"),
        ("matricula", "update", "all"),
        ("documento", "create", "all"),
        ("documento", "read", "all"),
        ("documento", "update", "all"),
        ("turma", "create", "all"),
        ("turma", "read", "all"),
        ("turma", "update", "all"),
        ("comunicado", "create", "all"),
        ("comunicado", "read", "all"),
        ("comunicado", "update", "all"),
        ("financeiro", "read", "all"),
        ("financeiro", "consumption", "all"),
        ("financeiro", "refund", "all"),
        ("relatorio", "read", "administrativo"),
        ("configuracao", "read", "instituicao"),
        ("configuracao", "update", "instituicao"),
        ("frequencia", "read", "all"),
        ("nota", "read", "all"),
    ],
    "professor": [
        ("aluno", "read", "own_turma"),
        ("aula", "create", "own"),
        ("aula", "read", "own"),
        ("aula", "update", "own"),
        ("chamada", "create", "own"),
        ("chamada", "read", "own"),
        ("chamada", "update", "own"),
        ("atividade", "create", "own"),
        ("atividade", "read", "own"),
        ("atividade", "update", "own"),
        ("nota", "create", "own"),
        ("nota", "read", "own"),
        ("nota", "update", "own"),
        ("comunicado", "create", "own_turma"),
        ("relatorio", "read", "pedagogico_own"),
        ("turma", "read", "own"),
        ("disciplina", "read", "own"),
    ],
    "responsavel": [
        ("aluno", "read", "own"),
        ("nota", "read", "own_alunos"),
        ("frequencia", "read", "own_alunos"),
        ("financeiro", "read", "own_alunos"),
        ("financeiro", "recarga", "own_alunos"),
        ("financeiro", "statement", "own_alunos"),
        ("comunicado", "read", "own"),
        ("documento", "create", "own"),
        ("documento", "read", "own"),
        ("relatorio", "read", "own_alunos"),
        ("usuario", "read", "self"),
        ("usuario", "update", "self"),
    ],
}


class PermissionChecker:
    @staticmethod
    def has_permission(perfil: Perfil, recurso: str, acao: str, escopo: str) -> bool:
        if perfil not in REGISTRY:
            return False
        for r, a, e in REGISTRY[perfil]:
            if (r == "*" and a == "*" and e == "*") or (r == recurso and a == acao and e == escopo):
                return True
            if r == recurso and a == acao and e == "*":
                return True
            if r == recurso and a == "*" and e == escopo:
                return True
        return False
