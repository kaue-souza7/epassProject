# Atena — assistente de IA local do ePass

Assistente conversacional que responde **qualquer pergunta sobre dados do
sistema**, respeitando o perfil de quem pergunta. Roda 100% local (Ollama):
nenhuma requisição de dado sai da máquina.

---

## A regra que estrutura tudo

O LLM **não escolhe** tabela, coluna, filtro, aluno, turma nem usuário, e não
executa nada. Ele entra em **um** lugar da cadeia — passo 7 — para redigir um
texto a partir de fatos que o backend já autorizou.

```
JWT → perfil → allowlist → classificação → escopo → contexto → LLM → guardrails → resposta
     1        2         3          4             5        6          7         8        9
```

Os passos 1 a 6 e o 8 são determinísticos, em código. Se qualquer um deles
falhar, a resposta é uma recusa — nunca uma inferência.

| Passo | Arquivo | O que garante |
|---|---|---|
| 3 | `intent.py` | só existe o que o perfil pode perguntar |
| 4 | `intent.py` | a pergunta é mapeada por sinônimos, sem LLM |
| 5 | `context/*.py` | o escopo é resolvido **antes** de qualquer consulta |
| 6 | `context/*.py` | só dados não sensíveis, formatados e truncados |
| 7 | `ollama_client.py` | inferência pura: sem ferramentas, sem escrita |
| 8 | `guardrails.py` | todo número da resposta precisa existir no contexto |

---

## Camadas

| Arquivo | Responsabilidade |
|---|---|
| `ollama_client.py` | HTTP, retry, circuit breaker, semáforo, streaming |
| `intent.py` | catálogo de **46 intenções** + allowlist por perfil |
| `context/` | resolve escopo → consulta autorizada → fatos formatados |
| `prompt.py` | personalidade e montagem do prompt |
| `guardrails.py` | validação mecânica da resposta (anti-alucinação) |
| `service.py` | orquestração das etapas |
| `router.py` | `/ai/health`, `/ai/chat`, `/ai/chat/stream`, `/ai/conversas*` |
| `conversa.py` | cortesia em Python puro ("olá", "obrigado") |
| `mensagens.py` | todo texto que o usuário vê + barreira anti-vazamento |

Nenhuma camada fora de `context/` e `router.py` importa `app.database`.
`ollama_client.py` não tem acesso a banco: essa é a **garantia estrutural** de
que a IA não consulta dados.

---

## Cobertura por perfil

A allowlist é revisada em code review — `tests/test_ai_intent.py::test_matriz_de_permissao_fica_explicita`
trava a matriz, e `test_cada_perfil_tem_sugestoes_e_elas_passam_pelo_classificador`
impede que a tela mostre um atalho que o classificador não entende.

| Perfil | Intenções | Pode perguntar sobre |
|---|---|---|
| `responsavel` | 18 | notas, média, histórico, boletim, faltas, ocorrências, avisos, respostas, notificações, saldo, extrato, pedidos e programação de lanche, documentos, agenda, pulseira, matrícula, histórico escolar |
| `professor` | 11 | turmas, lista de alunos, médias, frequência, avaliações sem nota, ocorrências, avisos das turmas, prazos de boletim, chamadas |
| `secretaria` / `admin` | 19 | matrículas, alunos sem matrícula, ocupação de turmas, séries, documentos pendentes, ocorrências abertas, matrículas recentes, alocações, pedidos e estoque de cantina, avisos não lidos, saldo de aluno, agenda |
| `coordenador` | 7 | panorama da escola, turmas críticas, alunos que precisam de atenção, ocorrências abertas, avisos não lidos, matrículas, agenda |
| `cantineiro` | 5 | pedidos de hoje, cardápio, estoque, saldo do aluno, agenda |

`COORDENADOR` e `CANTINEIRO` nasceram com allowlist **vazia** — qualquer pergunta
caía em "não tenho acesso", embora o RBAC (`app/core/permissions.py`) já lhes
dessescopo real. Isso está travado pelo teste
`test_todo_perfil_responde_algo`.

---

## Anti-alucinação numérica

O guardrail mais importante para dado escolar: **todo número presente na
resposta precisa existir nos fatos autorizados**, comparado por valor e não por
texto (`8,5` = `8.50` = `8.5`).

É por isso que os builders calculam em SQL/SQLAlchemy e formatam em pt-BR antes
de entregar: o número que o modelo pode falar já está escrito no contexto. Se o
cálculo não foi feito, o modelo não tem como produzi-lo.

Teste que impede a regressão mais cara do módulo:
`test_guardrail_aceita_todo_numero_do_contexto` — garante que o guardrail **não**
corta um número que veio do próprio contexto (senão uma resposta correta viraria
"prefiro não afirmar").

---

## Cálculos compartilhados

`context/comum.py` concentra média ponderada, frequência e situação estimada.
Motivo: os mesmos números aparecem em intenções de perfis diferentes, e três
versões do mesmo cálculo divergiriam entre si — a IA passaria a discordar do
boletim. Os cálculos espelham `reports/service.py` e `dashboard/repository.py`.

Regras que valem em qualquer lugar:

- **frequência** = presentes / total de registros; falta justificada conta como
  presença;
- **média** = `Σ(nota × peso) / Σ(peso)` por disciplina; recuperação não entra;
- **média geral** não é a média das médias — cada disciplina entra com o peso
  das suas avaliações;
- **situação** reprova por frequência abaixo do mínimo, independentemente da
  nota.

---

## Detalhes que sustentam a confiança

- **Boletim só depois de liberado.** `boletim_aluno` só mostra o que existe em
  `liberacoes_boletim`, igual ao `reports/service.py`. Sem isso a assistente
  seria o caminho mais fácil de burlar a data de publicação.
- **Cantineiro vê saldo, não extrato.** O RBAC dá `read_wallet` e não
  `statement`; `saldo_aluno_cantina` nunca lista movimentações.
- **Pedido de escopo amplo é barrado antes do casamento.** "Quantos alunos estão
  matriculados?" contém "matriculado", que casaria com uma intenção de escopo
  pessoal. A checagem de escopo vem antes, senão o responsável receberia a
  média do filho em vez de um "não".
- **Cobertura catálogo↔builder verificada no boot.** `verificar_cobertura()` no
  `router.py`: intenção sem builder vira recusa em vez de consulta genérica.
- **Rate limit por usuário**, não por IP (`chave_por_usuario`): atrás de proxy
  todo mundo compartilha o IP, e limitar por IP puniria os usuários honestos.
- **Recusa diz o que dá para perguntar** (`mensagens.escopo_do_perfil`). Recusa
  que não oferece caminho vira beco sem saída na tela.

---

## Configuração

Tudo em `AI_*` / `OLLAMA_*` (ver `.env.example`). O que mais importa:

| Variável | Papel |
|---|---|
| `AI_ENABLED` | desliga o assistente sem afetar o SGE |
| `OLLAMA_MODEL` | modelo local (`qwen3:4b`); o `ollama-bootstrap` baixa este tag |
| `OLLAMA_MAX_CONCURRENCY` | 1 = serializa; a 2ª pergunta entra na fila |
| `AI_CONTEXT_MAX_CHARS` | teto do contexto enviado ao modelo |
| `AI_RATE_LIMIT` | cota de perguntas por usuário |
| `AI_HISTORY_TURNS` / `AI_HISTORY_MAX_CHARS` | quanto da conversa vai no prompt |

**A IA nunca derruba o SGE.** Se o Ollama cair, `/api/v1/health` continua 200 e
só `/ai/*` responde degradado. O `docker-compose.yml` usa
`condition: service_started` para o Ollama, nunca `service_healthy`.

---

## Testes

| Arquivo | O que trava |
|---|---|
| `tests/test_ai_intent.py` | catálogo, allowlist por perfil, escopo amplo |
| `tests/test_ai_conversa.py` | cortesia, barreira anti-vazamento, sugestões |
| `tests/test_ai_client.py` | resiliência: retry, circuit breaker, semáforo |
| `tests/test_ai_stream.py` | SSE, cancelamento, liberação da vaga |
| `tests/test_ai_history.py` | histórico, truncamento, anti-IDOR |
| `tests/integration/test_ai_context_builders.py` | escopo de **cada** builder + guardrail numérico |
| `tests/integration/test_ai_chat.py` | endpoints, persistência, isolamento entre usuários |
| `tests/integration/test_ai_conversa.py` | produto: cortesia e recusas por HTTP |
| `tests/integration/test_ai_seguranca.py` | escopo, IDOR, prompt injection, desescarar |

Ao adicionar uma intenção, o checklist é: entrada em `INTENCOES` → builder em
`context/` → registro em `REGISTRO` → sugestão por perfil (se couber na tela).
`verificar_cobertura()` e a matriz de permissões garantem que nada disso
esqueça.
