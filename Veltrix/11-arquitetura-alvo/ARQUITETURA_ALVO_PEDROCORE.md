# Arquitetura-Alvo do Veltrix

> Nota DOCFIX: este documento nasceu como planejamento da frente `PEDROCORE-REPLAN-01C`. Em `v7.0.0`, Task Router, Prompt Builder, Project Context, Artifact Reader opt-in, orchestration, structured warnings/responses e audit não persistente já existem no lado Veltrix. Use [[../00_MAPEAMENTO_GERAL_PEDROCORE]] como arquitetura atual canônica.

## 1. Snapshot histórico da arquitetura antes da orquestração

Na época da redação original, o backend (`apps/api/app`) era organizado assim:

```
FastAPI (app/main.py)
└── router /api (app/modules/chat/router.py)
    ├── POST /api/chat      → ChatService.send_message
    └── GET  /api/providers → ChatService.list_providers
            │
            ▼
      ChatService (app/modules/chat/service.py)
            │
            ▼
      ProviderRegistry (app/modules/providers/registry.py)
            │
            ├── MockProvider
            ├── GeminiProvider
            ├── OpenAIProvider
            ├── ClaudeProvider
            ├── DeepSeekProvider
            └── GrokProvider
                 (todos herdam de BaseAIProvider, app/modules/providers/base.py)
```

Comportamento naquela fase:

- `ChatService` resolve o provider pedido (`payload.provider`) no `ProviderRegistry`.
- Se o provider não existe ou falha (chave ausente, erro de execução), `ChatService` aciona fallback automático para `MockProvider`.
- Cada provider monta seu próprio prompt usando `BaseAIProvider.build_prompt`, um template fixo por `mode` (`normal`, `tecnico`, `resumido`, `codigo`).
- A resposta é sempre texto livre (`answer: str`), sem diferenciação por tipo de tarefa.
- O frontend React/Vite/TypeScript consome hoje apenas esses dois endpoints, via `apps/web/src/services/api.ts`.

**Esse snapshot histórico funcionava para chat multi-provider simples, mas foi superado**: o estado atual adicionou `task_type`, `origin_system`, Project Context, artefatos, QA textual, release gate, orchestration, warnings estruturados e audit não persistente.

## 2. Arquitetura-alvo que guiou a implementação

Fluxo conceitual futuro:

```
Sistema externo (ex.: FinGuard)
        │
        ▼
   Veltrix API  (`POST /api/orchestrate`, ver seção 10)
        │
        ▼
   Task Router               ← classifica task_type/origin_system, decide estratégia
        │
        ▼
   Project Context           ← resolve limites e metadados do sistema de origem
        │
        ▼
   Artifact Reader           ← se houver artifacts no payload (somente leitura)
        │
        ▼
   Prompt Builder            ← monta o prompt final a partir de tudo acima
        │
        ▼
   Provider Orchestration    ← escolhe provider/modelo e executa a chamada
        │
        ▼
   Structured Responses      ← formata a resposta conforme o task_type
        │
        ▼
   Audit/logs                ← registra a chamada (sem dados sensíveis)
        │
        ▼
   Resposta para o sistema de origem
```

Esta arquitetura foi parcialmente materializada no core atual. Provider Orchestration avançada e logs persistentes continuam opcionais/futuros; os demais módulos principais existem em `apps/api/app/modules/`. O detalhamento histórico de cada módulo está em documentos próprios:

- [`TASK_ROUTER.md`](./TASK_ROUTER.md)
- [`PROMPT_BUILDER.md`](./PROMPT_BUILDER.md)
- [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md)

Os demais módulos (Provider Orchestration, Structured Responses, Artifact Reader, Audit/logs) estão detalhados nas seções 6 a 9 deste documento, por serem transversais e não exigirem um documento dedicado nesta fase.

## 3–5. Task Router, Prompt Builder e Project Context

Ver documentos dedicados: [`TASK_ROUTER.md`](./TASK_ROUTER.md), [`PROMPT_BUILDER.md`](./PROMPT_BUILDER.md), [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md).

## 6. Provider Orchestration (evolução planejada do `ProviderRegistry`)

### Hoje (implementado)

- Provider escolhido manualmente pelo campo `provider` do payload, ou pelo `default_provider` das configurações (`mock`, se nada for informado).
- Fallback direto e incondicional para `MockProvider` em qualquer falha (config ausente ou erro de execução), sem diferenciação por tipo de tarefa.

### Futuro (planejado, não implementado)

- Seleção de provider por `task_type` (ex.: tarefas de análise de QA preferindo um provider com melhor desempenho analítico).
- Seleção considerando custo, disponibilidade e qualidade esperada — critérios ainda a definir tecnicamente.
- Política de fallback diferenciada por tarefa: fallback simples para tarefas não críticas (`general_chat`), mas **warning forte** ou bloqueio de conclusão para tarefas críticas (`qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`), conforme já fixado nas Decisões Técnicas 014 e 020.
- Proibição explícita de tratar uma resposta via `MockProvider` como validação confiável em qualquer fluxo crítico — isso vale tanto para o contrato de resposta (`docs/10-contratos/`) quanto para a lógica interna de orquestração que viria a existir aqui.

## 7. Structured Responses

- O chat comum (`general_chat`, `technical_explanation`, `code_help`) pode continuar respondendo com `answer` livre, como hoje.
- Tarefas críticas usam campos estruturados na resposta atual: `qa`, `release_gate`, `warnings`, `warning_codes`, `blocked_reason`, `status` e `audit`.
- O objetivo é que sistemas externos consumam a resposta programaticamente (parseando campos), sem depender de um humano lendo texto livre para decidir o que fazer.
- Em `v7.0.0`, há schemas Pydantic para `ChatResponse`, `OrchestrateResponse`, `QAResponseSkeleton`, `ReleaseGateResult`, `VisualQAAnalysis`, `ExplorationPlan` e `AuditMetadata`.

## 8. Artifact Reader

- No uso padrão, artefatos são recebidos **via payload** (`artifacts[].content`).
- O Artifact Reader existe como recurso opt-in controlado: `PEDROCORE_ARTIFACT_READER_ENABLED=true` + `PEDROCORE_ARTIFACT_ALLOWED_DIRS`.
- Ele bloqueia path traversal, `.env`, binário, segredo, arquivo grande, extensão fora da lista e qualquer caminho contendo "finguard".
- **O FinGuard não é lido automaticamente.** Origem `finguard`/`finguard-local` não usa Artifact Reader; deve enviar conteúdo por payload.
- Regra permanente: o Artifact Reader nunca escreve, nunca comita e nunca executa comandos.

## 9. Audit/logs

Campos atuais de auditoria não persistente por chamada:

- `origin_system`
- `task_type`
- `provider` usado
- `fallback_used`
- `error` (se houver)
- `latência` (tempo de resposta)
- `timestamp`
- se a resposta foi estruturada (`response_type`)
- se a tarefa era crítica

**Sem armazenar chaves de API ou dados sensíveis do conteúdo da mensagem/artefatos.** Nenhum banco de dados, tabela ou mecanismo de persistência de auditoria existe hoje; isso é planejamento para orientar decisões futuras de implementação (fora do escopo desta fase, que é só documentação).

## 10. Relação com o endpoint atual `/api/chat`

- `POST /api/chat` **continua existindo** e não é removido nem alterado por este planejamento.
- `/api/chat` seguirá atendendo o uso conversacional atual (o chat da interface web do Veltrix).
- O contrato de orquestração atual é exposto em `POST /api/orchestrate`.
- A evolução arquitetural não quebrou o frontend atual: `/api/orchestrate` coexiste com `/api/chat`, sem substituí-lo de forma disruptiva.
- Frontend e design permanecem congelados durante toda a reformulação (`PEDROCORE-REPLAN-01`, Decisão Técnica 015) — nenhuma mudança de UI é necessária ou prevista para esta arquitetura-alvo.

## 11. Relação com o FinGuard (reforço, no contexto da arquitetura)

- O FinGuard é projeto externo e independente.
- O QA Automation do FinGuard (validação de API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências) pertence ao FinGuard; o Veltrix não o executa, não o substitui e não roda comandos dentro dele.
- O Veltrix pode analisar relatórios e evidências **recebidos** (via payload, nunca por acesso direto ao repositório do FinGuard).
- O Veltrix não altera o FinGuard: não roda migrations, não roda seed/reset, não comita nele.
- O Veltrix não calcula números financeiros oficiais do FinGuard.
- Exploração assistida/manual existe do lado Veltrix como `exploration`, sempre com `can_execute_actions=false`; QA visual real/autônoma permanece não executada.
