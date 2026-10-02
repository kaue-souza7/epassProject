"""Módulo de IA local "Atena" (Ollama).

Camadas:
  - `ollama_client`  cliente HTTP (timeout, retry, circuit breaker, semáforo)
  - `intent`         roteador DETERMINÍSTICO de intenções + allowlist por perfil
  - `context/`       context builders: escopo → consulta autorizada → fatos
  - `prompt`         personalidade e montagem do prompt
  - `guardrails`     validação mecânica da resposta (anti-alucinação)
  - `service`        orquestração das etapas
  - `router`         `/ai/health` e `/ai/chat`

Nenhuma camada desta hierarquia importa `app.database` fora de `context/` e
`router` (que recebem a sessão por dependency). O cliente do Ollama não tem
acesso a banco: é a garantia estrutural de que a IA não consulta dados.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
