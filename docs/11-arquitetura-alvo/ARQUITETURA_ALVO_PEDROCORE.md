# Arquitetura-Alvo do PedroCore IA (Planejada)

> Parte da frente `PEDROCORE-REPLAN-01C`. Este documento descreve a arquitetura **atual** (o que já existe e funciona hoje) e a arquitetura **alvo/planejada** (o que guiará a evolução futura do PedroCore). Nada na seção de arquitetura-alvo está implementado: não há Task Router, Prompt Builder, Project Context, Provider Orchestration avançada, Structured Responses, Artifact Reader ou Audit/logs no código hoje. O PedroCore continua sendo, hoje, apenas uma API de chat multi-provider (`POST /api/chat`, `GET /api/providers`).

## 1. Arquitetura atual (implementada)

O backend hoje (`apps/api/app`) é organizado assim:

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

Comportamento atual:

- `ChatService` resolve o provider pedido (`payload.provider`) no `ProviderRegistry`.
- Se o provider não existe ou falha (chave ausente, erro de execução), `ChatService` aciona fallback automático para `MockProvider`.
- Cada provider monta seu próprio prompt usando `BaseAIProvider.build_prompt`, um template fixo por `mode` (`normal`, `tecnico`, `resumido`, `codigo`).
- A resposta é sempre texto livre (`answer: str`), sem diferenciação por tipo de tarefa.
- O frontend React/Vite/TypeScript consome hoje apenas esses dois endpoints, via `apps/web/src/services/api.ts`.

**Essa arquitetura funciona bem para chat multi-provider simples, mas é limitada para orquestração central por tarefas**: não há conceito de tipo de tarefa (`task_type`), de sistema de origem (`origin_system`), de contexto de projeto, de artefato anexado, de resposta estruturada ou de auditoria — tudo isso precisaria ser adicionado para o PedroCore atuar como orquestrador central do ecossistema Pedro, conforme os contratos já especificados em `docs/10-contratos/`.

## 2. Arquitetura-alvo (planejada, não implementada)

Fluxo conceitual futuro:

```
Sistema externo (ex.: FinGuard)
        │
        ▼
   PedroCore API  (endpoint futuro, ver seção 10)
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

Esta é uma arquitetura **planejada**. Nenhum destes módulos existe hoje em `apps/api`. O detalhamento de cada módulo está em documentos próprios:

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

## 7. Structured Responses (planejada)

- O chat comum (`general_chat`, `technical_explanation`, `code_help`) pode continuar respondendo com `answer` livre, como hoje.
- Tarefas críticas exigem um schema de resposta, não apenas texto: ver o formato de QA já especificado em `docs/10-contratos/CONTRATO_QA_INTELLIGENCE.md` (`status`, `risk_level`, `summary`, `failures`, `probable_causes`, `suggested_commands`, `can_advance`, `confidence`).
- O objetivo é que sistemas externos consumam a resposta programaticamente (parseando campos), sem depender de um humano lendo texto livre para decidir o que fazer.
- Nesta fase, isso é apenas o **formato planejado**; não há serializador, schema Pydantic ou lógica de validação implementados.

## 8. Artifact Reader (camada futura, não implementada)

- Nesta fase, artefatos só podem ser recebidos **via payload** (`artifacts[].content`), exatamente como especificado em `docs/10-contratos/CONTRATO_ORQUESTRACAO.md`, seção 6.
- **Não existe leitura automática de pastas externas.** Nenhum caminho de diretório de outro projeto é acessado pelo PedroCore hoje ou nesta fase de planejamento.
- Integração com caminhos reais (ex.: ler diretamente `qa/reports/` de um repositório externo) é explicitamente **fase futura**, fora do escopo de `PEDROCORE-REPLAN-01C`.
- **O FinGuard não deve ser lido automaticamente nesta etapa** — nenhuma leitura de arquivo do FinGuard ocorre nesta frente de trabalho, nem pelo Artifact Reader planejado, que ainda não existe.
- Artefatos Markdown do QA Automation do FinGuard são um **caso de uso futuro**, já antecipado no contrato de QA Intelligence, mas dependem de o Artifact Reader existir e de uma decisão explícita de integração.
- Regra permanente de design: o Artifact Reader, quando implementado, **nunca escreve, nunca comita e nunca executa comandos** em projetos externos — é estritamente somente leitura, e mesmo a leitura, nesta fase, é limitada a conteúdo enviado no payload.

## 9. Audit/logs (necessidade futura, não implementada)

Campos planejados para um futuro registro de auditoria de cada chamada:

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
- `/api/chat` seguirá atendendo o uso conversacional atual (o chat da interface web do PedroCore).
- O contrato futuro de orquestração (`docs/10-contratos/CONTRATO_ORQUESTRACAO.md`) poderia futuramente ser exposto em um endpoint novo, conceitualmente algo como `/api/orchestrate` (nome ilustrativo, não definido nem implementado).
- A evolução arquitetural não pode quebrar o frontend atual: qualquer novo endpoint coexistiria com `/api/chat`, nunca o substituindo de forma disruptiva.
- Frontend e design permanecem congelados durante toda a reformulação (`PEDROCORE-REPLAN-01`, Decisão Técnica 015) — nenhuma mudança de UI é necessária ou prevista para esta arquitetura-alvo.

## 11. Relação com o FinGuard (reforço, no contexto da arquitetura)

- O FinGuard é projeto externo e independente.
- O QA Automation do FinGuard (validação de API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências) pertence ao FinGuard; o PedroCore não o executa, não o substitui e não roda comandos dentro dele.
- O PedroCore poderá, no futuro, analisar relatórios e evidências **recebidos** (via payload, nunca por acesso direto ao repositório do FinGuard).
- O PedroCore não altera o FinGuard: não roda migrations, não roda seed/reset, não comita nele.
- O PedroCore não calcula números financeiros oficiais do FinGuard.
- `QA-AUTOMATION-01G` (agente exploratório de QA) é um caso de uso futuro planejado (ver `docs/10-contratos/CONTRATO_QA_INTELLIGENCE.md`), não uma implementação atual.
