# PedroCore IA — Contratos Técnicos (Índice)

> Documento de planejamento da frente `PEDROCORE-REPLAN-01B`. Todo o conteúdo aqui é **contrato futuro/planejado**. Nada descrito neste documento ou nos documentos referenciados existe hoje no código (`apps/api`). Não há endpoint novo, schema Python, service, migration, banco de dados ou leitor de artefatos implementado nesta etapa — apenas especificação em Markdown.

## Objetivo

Documentar, antes de qualquer implementação, os contratos técnicos que vão guiar a evolução do PedroCore IA de "API de chat multi-provider" para **orquestrador central de IA do ecossistema Pedro**, consumível por sistemas externos.

## Estado atual vs. planejado

| Item | Estado |
|---|---|
| `POST /api/chat` com `{ message, mode, provider, model, system_prompt }` | **Atual** — implementado e funcional hoje. |
| `GET /api/providers` | **Atual** — implementado e funcional hoje. |
| Contrato de orquestração (`origin_system`, `task_type`, `context`, `artifacts`) | **Planejado** — especificado neste conjunto de documentos, não implementado. |
| Resposta estruturada por tipo de tarefa | **Planejado** — não implementado. |
| Task Router / Prompt Builder / Project Context | **Planejado** — arquitetura-alvo da fase `PEDROCORE-REPLAN-01C`, ainda não desenhada em detalhe de módulos. |
| Artifact Reader (leitura automática de pastas/arquivos externos) | **Futuro** — fora de escopo desta fase; nesta fase só se planeja recebimento de conteúdo via payload. |
| QA Intelligence | **Futuro** — caso de uso planejado, ver `CONTRATO_QA_INTELLIGENCE.md`. Não implementado. |
| Integração real com o FinGuard | **Inexistente** — não há, hoje, nenhuma leitura, escrita ou chamada ao FinGuard. |

## Documentos desta frente

- [`CONTRATO_ORQUESTRACAO.md`](./CONTRATO_ORQUESTRACAO.md) — contrato geral de entrada/saída, campos obrigatórios/opcionais, tipos de tarefa (`task_type`), contrato de artefatos, `provider_preference` e regras de fallback.
- [`CONTRATO_QA_INTELLIGENCE.md`](./CONTRATO_QA_INTELLIGENCE.md) — formato de resposta estruturada para tarefas de QA, relação com o FinGuard e limites de atuação.

## Princípios gerais que todos os contratos seguem

1. **Nada aqui é implementação.** Todo exemplo de JSON é conceitual/ilustrativo, para orientar o design futuro.
2. **Diferenciação explícita** entre o que já existe (`atual`), o que está desenhado mas não codificado (`planejado`) e o que depende de decisões futuras (`futuro`).
3. **Segurança de providers reais**: nenhum contrato aqui autoriza chamada automática a Gemini/OpenAI/Claude/DeepSeek/Grok; a escolha de provider real continua exigindo chave configurada e, no desenho futuro, controle explícito adicional (ver Decisão Técnica 013).
4. **Fallback não é validação**: em nenhuma hipótese um contrato futuro pode tratar uma resposta gerada via fallback (`MockProvider`) como equivalente a uma resposta real para tarefas críticas (ver Decisão Técnica 014 e 020).
5. **FinGuard é sempre externo e somente leitura**: nenhum contrato aqui prevê escrita, execução de comando, migration, seed/reset ou commit em qualquer projeto externo, incluindo o FinGuard (ver Decisão Técnica 009 e 010).
6. **Artefatos por payload, não por acesso a pasta**: nesta fase, qualquer artefato (relatório de QA, log, etc.) só é considerado recebido se vier no corpo da requisição; leitura automática de diretórios de outros projetos é explicitamente fora de escopo (ver Decisão Técnica 019).

## Relação resumida com o FinGuard nestes contratos

- O FinGuard é projeto externo; o PedroCore não altera, não roda migrations, não roda seed/reset e não comita nele.
- O QA Automation do FinGuard (validação técnica: API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E) continua pertencendo ao FinGuard.
- Apenas a frente `QA-AUTOMATION-01G` (agente exploratório de QA) foi delegada ao PedroCore como caso de uso futuro — detalhado em `CONTRATO_QA_INTELLIGENCE.md`.
- O PedroCore não calcula números financeiros oficiais do FinGuard.
- Relatórios de QA do FinGuard hoje são Markdown livre, não JSON estruturado — os contratos futuros de artefato precisam tolerar isso (ver `CONTRATO_ORQUESTRACAO.md`, seção de artefatos).
