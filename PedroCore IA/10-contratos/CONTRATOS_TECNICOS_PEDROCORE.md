# PedroCore IA — Contratos Técnicos (Índice)

> Nota DOCFIX: este documento nasceu como planejamento da frente `PEDROCORE-REPLAN-01B`. Em `v7.0.0`, parte relevante desses contratos já foi implementada no lado PedroCore. Use [[../00_MAPEAMENTO_GERAL_PEDROCORE]] como mapa atual e leia este arquivo como histórico/contrato de origem.

## Objetivo

Documentar, antes de qualquer implementação, os contratos técnicos que vão guiar a evolução do PedroCore IA de "API de chat multi-provider" para **orquestrador central de IA do ecossistema Pedro**, consumível por sistemas externos.

## Estado atual vs. planejado

| Item | Estado |
|---|---|
| `POST /api/chat` com `{ message, mode, provider, model, system_prompt }` | **Atual** — implementado e funcional hoje. |
| `GET /api/providers` | **Atual** — implementado e funcional hoje. |
| Contrato de orquestração (`origin_system`, `task_type`, `context`, `artifacts`) | **Implementado no lado PedroCore** em `/api/orchestrate`; cliente externo ainda é frente separada. |
| Resposta estruturada por tipo de tarefa | **Implementada parcialmente**: `qa`, `release_gate`, `visual_qa_analysis`, `exploration`, warnings e audit. |
| Task Router / Prompt Builder / Project Context | **Implementados** como módulos em `apps/api/app/modules/`. |
| Artifact Reader (leitura automática de pastas/arquivos externos) | **Implementado como opt-in controlado**, default-off e bloqueado para FinGuard. |
| QA Intelligence | **Implementada como heurística textual local**; IA real/visual real permanece fora do padrão. |
| Integração real com o FinGuard | **Pronta no lado PedroCore por contrato HTTP**; cliente no repositório FinGuard ainda não implementado aqui. |

## Documentos desta frente

- [`CONTRATO_ORQUESTRACAO.md`](./CONTRATO_ORQUESTRACAO.md) — contrato geral de entrada/saída, campos obrigatórios/opcionais, tipos de tarefa (`task_type`), contrato de artefatos, `provider_preference` e regras de fallback.
- [`CONTRATO_QA_INTELLIGENCE.md`](./CONTRATO_QA_INTELLIGENCE.md) — formato de resposta estruturada para tarefas de QA, relação com o FinGuard e limites de atuação.

## Princípios gerais que todos os contratos seguem

1. **Este documento é histórico de planejamento.** O estado atual implementado está em [[../00_MAPEAMENTO_GERAL_PEDROCORE]].
2. **Diferenciação explícita** entre o que já existe (`atual`), o que está desenhado mas não codificado (`planejado`) e o que depende de decisões futuras (`futuro`).
3. **Segurança de providers reais**: nenhum contrato aqui autoriza chamada automática a Gemini/OpenAI/Claude/DeepSeek/Grok; a escolha de provider real continua exigindo chave/configuração e `allow_real_provider=true` (ver Decisão Técnica 013).
4. **Fallback não é validação**: em nenhuma hipótese um contrato atual ou futuro pode tratar uma resposta gerada via fallback (`MockProvider`) como equivalente a uma resposta real para tarefas críticas (ver Decisão Técnica 014 e 020).
5. **FinGuard é sempre externo e somente leitura**: nenhum contrato aqui prevê escrita, execução de comando, migration, seed/reset ou commit em qualquer projeto externo, incluindo o FinGuard (ver Decisão Técnica 009 e 010).
6. **Artefatos por payload, não por acesso a pasta**: nesta fase, qualquer artefato (relatório de QA, log, etc.) só é considerado recebido se vier no corpo da requisição; leitura automática de diretórios de outros projetos é explicitamente fora de escopo (ver Decisão Técnica 019).

## Relação resumida com o FinGuard nestes contratos

- O FinGuard é projeto externo; o PedroCore não altera, não roda migrations, não roda seed/reset e não comita nele.
- O QA Automation do FinGuard (validação técnica: API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E) continua pertencendo ao FinGuard.
- O lado PedroCore implementa exploração assistida/manual como plano, sem execução autônoma — detalhado em `CONTRATO_QA_INTELLIGENCE.md` e no mapa geral.
- O PedroCore não calcula números financeiros oficiais do FinGuard.
- Relatórios de QA do FinGuard hoje são Markdown livre, não JSON estruturado — os contratos de artefato precisam tolerar isso (ver `CONTRATO_ORQUESTRACAO.md`, seção de artefatos).
