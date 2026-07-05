# PedroCore IA — Roadmap

> Documento oficial de roadmap. Substitui a leitura anterior deste arquivo e a versão paralela em `docs/03_ROADMAP.md` (a ser consolidada/tratada em etapa futura). Nenhuma data é prometida; status refletem apenas conclusão ou planejamento.

## Entregas concluídas

### V1 — Chat/API mock

Status: CONCLUÍDA.

### V2 — Multi-provider inicial / Gemini real

Status: CONCLUÍDA.

Entregas: `BaseAIProvider`, `ProviderRegistry`, `MockProvider`, `GeminiProvider`, `OpenAIProvider`, `ClaudeProvider`, `DeepSeekProvider`, `GrokProvider`, fallback automático para Mock, endpoint `/api/providers`, seletor de provider no frontend.

### V3 — Histórico local / feedback

Status: CONCLUÍDA.

Histórico de mensagens em `localStorage`, feedback "gostei"/"não gostei" por resposta.

### V4 — Componentização / interface

Status: CONCLUÍDA.

Separação da interface em componentes React (`ChatSidebar`, `MessageBubble`, `ChatComposer`, `LoadingBubble`, `ErrorBanner`).

### V5.1.9 — Interface sem ícones internos / topo limpo

Status: CONCLUÍDA.

Última entrega visual: remoção definitiva de ícones residuais do topo interno, preservando layout, responsividade e painel de providers.

---

## PEDROCORE-REPLAN-01 — Reformulação documental, estratégica e arquitetural

Frente aberta para reposicionar o PedroCore como orquestrador central de IA do ecossistema Pedro, antes de qualquer nova implementação de código. Sem datas prometidas.

**Status geral: concluída no escopo documental.** Todas as subfases (01A a 01E) estão commitadas. Nenhuma implementação de código foi feita nesta frente — o que foi entregue é exclusivamente visão, contratos, arquitetura-alvo e planejamento de QA Intelligence, documentados em Markdown. Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md` para o fechamento consolidado.

- **01A — Consolidação documental e visão oficial.** *(concluída)* Reformulou a documentação principal (README, VERSION, visão geral, objetivo, roadmap, status, decisões técnicas, changelog) para refletir a nova visão estratégica, sem alterar código. Commitada em `1e5a8cb`.
- **01B — Planejamento técnico e contratos.** *(concluída)* Especificou, em `docs/10-contratos/`, os contratos de request/response para consumo por sistemas externos (`origin_system`, `task_type`, `context`, `artifacts`), tipos de tarefa, resposta estruturada, contrato de artefatos, roteamento de provider e regras de fallback — sem implementar código. Commitada em `6e7badd`.
- **01C — Arquitetura-alvo: Task Router, Prompt Builder, Project Context.** *(concluída)* Documentou, em `docs/11-arquitetura-alvo/`, a arquitetura-alvo que sustentaria os contratos da 01B: Task Router, Prompt Builder, Project Context, Provider Orchestration, Structured Responses, Artifact Reader e Audit/logs — sem implementar código. Commitada em `c1e7816`.
- **01D — Planejamento de QA Intelligence.** *(concluída)* Documentou, em `docs/12-qa-intelligence/`, a camada futura de QA Intelligence: análise de relatórios de QA (Markdown livre), diagnóstico de falhas, release gate assistido, resposta estruturada, severidade/risco e limites de atuação — sempre em modo somente leitura e sem implementar código. Commitada em `8c68b67`.
- **01E — Fechamento documental da reformulação.** *(concluída)* Consolidou o que foi entregue em 01A–01D em `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`, registrou pendências e riscos remanescentes, e recomendou a próxima fase. Documentação duplicada/legada tratada como pendência planejada (ver `docs/13-fechamento/`), não removida nesta etapa. Commitada em `cc808a7`.

## PEDROCORE-IMPLEMENT-01 — Base inicial de orquestração por task_type

Primeira frente de implementação de código pós-reformulação, detalhada em `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`, seção 12.

- **01A/01B — Task Router mínimo + metadados de resposta.** *(implementada, commitada)* Commitada em `577bc88`; correção documental em `20e6cff`. Testes backend passando (15/15 na época; ver abaixo o total atual).

  Implementado: `task_type` opcional no `ChatRequest` (default `"general_chat"`), `origin_system` opcional (default `"pedrocore"`), `context`/`metadata` opcionais, Task Router mínimo em `apps/api/app/modules/task_router/` (normaliza `task_type`, reconhece `general_chat`, `technical_explanation`, `code_help`, `qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `artifact_summary` e `unknown`, sem bloqueio duro), metadados de tarefa no `ChatResponse` (`task_type`, `origin_system`, `task_criticality`, `requires_structured_response`, `task_warnings`), warning forte em fallback crítico.

- **01C — Project Context mínimo.** *(implementada, em validação)* Módulo `apps/api/app/modules/project_context/`: `ProjectContextResolver.resolve(origin_system)` resolve configuração interna por sistema (`pedrocore`, `finguard`, `unknown`), com `read_only`, `can_execute_commands`, `can_write_files`, `allowed_tasks`, `warnings` e `notes`. Não lê arquivos externos, não acessa o FinGuard real — apenas devolve dados de configuração interna.

- **01D — Prompt Builder mínimo.** *(implementada, em validação)* Módulo `apps/api/app/modules/prompt_builder/`: monta `enriched_system_prompt` com seções `[Instruções do sistema]`, `[Tarefa]`, `[Origem]`, `[Limites do projeto]`, `[Contexto enviado]`, `[Metadata]`, `[Regras de segurança]` (com regra adicional quando `origin_system=finguard`). Não chama provider, não decide provider. `BaseAIProvider.build_prompt` continua existindo e intacto; providers reais não foram reescritos.

- **01E — Structured Response metadata.** *(implementada, em validação)* `ChatResponse` ganhou `project_id`, `project_read_only`, `project_can_execute_commands`, `project_can_write_files`, `response_style`, `audit_id`, `audit_timestamp`, todos com defaults seguros. Campos antigos (incluindo os da 01A/01B) preservados. Campos de QA Intelligence real (`findings`, `failures`, `risk_level`, `can_advance`, `suggested_commands`, `suggested_fixes`) **não** foram adicionados — pertencem a uma fase futura.

- **01F — Audit metadata não persistente.** *(implementada, em validação)* Módulo `apps/api/app/modules/audit/`: `AuditService.create()` gera `audit_id` (uuid4) e `timestamp` (ISO, UTC) em memória por requisição, sem banco, arquivo, middleware ou endpoint. `fallback_used` é atualizado ao final do fluxo.

- **01G — Testes de integração do fluxo orquestrado.** *(implementada, em validação)* Novos arquivos `apps/api/tests/test_project_context.py`, `test_prompt_builder.py` e `test_orchestration_flow.py`, cobrindo Project Context, Prompt Builder e o fluxo `/api/chat` de ponta a ponta (request antiga, `origin_system=finguard`, origem desconhecida, fallback crítico com audit, `requires_structured_response`, `/api/providers`).

- **01H — Proteção contra provider real em testes.** *(implementada, em validação)* Teste dedicado garante que o provider default é `mock`, que ele não é `real_provider` e está sempre configurado; toda a suíte usa apenas `mock`/provider inexistente.

- **01I — Orchestration module.** *(avaliada, adiada)* Não foi criado `apps/api/app/modules/orchestration/`. Justificativa: `ChatService.send_message` já encapsula o pipeline completo (Task Router → Project Context → Audit → Prompt Builder → Provider → fallback) em um ponto de entrada único e reutilizável; extrair um módulo de orquestração agora seria abstração prematura sem um segundo consumidor real. Fica registrado como pendência para quando um endpoint `/api/orchestrate` (ainda inexistente) vier a ser criado.

Ainda não existe: Artifact Reader real, QA Intelligence real, análise visual, banco de dados/persistência, autenticação entre sistemas, endpoint `/api/orchestrate`, integração real com o FinGuard, ou qualquer alteração de frontend/design.

## Fases futuras (planejadas, sem ordem de data fixa)

Dependentes da conclusão de `PEDROCORE-REPLAN-01` e sujeitas a repriorização:

- Task Router.
- Prompt Builder.
- Resposta estruturada (schemas por tipo de tarefa, além de texto livre).
- Auditoria/logs de chamadas (origem, provider usado, fallback, latência).
- Leitura controlada de artefatos Markdown (relatórios de QA, documentação Obsidian de projetos externos), sempre somente leitura.
- QA Intelligence (caso de uso concreto de análise de relatórios de QA do FinGuard).
- Persistência/histórico no backend (hoje o histórico existe apenas no `localStorage` do navegador).
- Integração controlada com sistemas externos, incluindo autenticação e identificação do sistema chamador.

Nenhum desses itens está implementado. Nenhuma integração com o FinGuard existe hoje — toda menção acima é planejamento futuro.

## Documentação de contratos (01B)

Os contratos técnicos planejados na fase `01B` estão detalhados em `docs/10-contratos/`:

- `docs/10-contratos/CONTRATOS_TECNICOS_PEDROCORE.md` — índice e princípios gerais.
- `docs/10-contratos/CONTRATO_ORQUESTRACAO.md` — contrato de entrada/saída, tipos de tarefa, artefatos, provider preference e fallback.
- `docs/10-contratos/CONTRATO_QA_INTELLIGENCE.md` — resposta estruturada de QA e limites com o FinGuard.

Esses documentos são especificação/planejamento. Nenhum contrato neles descrito está implementado no código.

## Documentação de arquitetura-alvo (01C)

A arquitetura-alvo que sustentaria os contratos da `01B` está detalhada em `docs/11-arquitetura-alvo/`:

- `docs/11-arquitetura-alvo/ARQUITETURA_ALVO_PEDROCORE.md` — arquitetura atual vs. arquitetura-alvo, Provider Orchestration, Structured Responses, Artifact Reader, Audit/logs, relação com `/api/chat` e com o FinGuard.
- `docs/11-arquitetura-alvo/TASK_ROUTER.md` — responsabilidade e exemplos de roteamento planejados.
- `docs/11-arquitetura-alvo/PROMPT_BUILDER.md` — responsabilidade planejada de montagem de prompt.
- `docs/11-arquitetura-alvo/PROJECT_CONTEXT.md` — conceito planejado de representação de sistemas externos.

Esses documentos são especificação/planejamento de arquitetura. Nenhum módulo neles descrito (Task Router, Prompt Builder, Project Context, Artifact Reader, Audit/logs) está implementado no código.

## Documentação de QA Intelligence (01D)

A camada futura de QA Intelligence está detalhada em `docs/12-qa-intelligence/`:

- `docs/12-qa-intelligence/QA_INTELLIGENCE_OVERVIEW.md` — definição, relação com o QA Automation do FinGuard, artefatos analisáveis, relatórios Markdown, resposta estruturada, severidade/risco, regra de avanço/bloqueio, fallback Mock, análise visual futura, limites/proibições e relação com a arquitetura-alvo (01C).
- `docs/12-qa-intelligence/QA_REPORT_ANALYSIS.md` — caso de uso `qa_report_analysis`.
- `docs/12-qa-intelligence/QA_FAILURE_DIAGNOSIS.md` — caso de uso `qa_failure_diagnosis`.
- `docs/12-qa-intelligence/QA_RELEASE_GATE.md` — caso de uso `release_gate_review`.

Esses documentos são especificação/planejamento. QA Intelligence **não está implementada** — não há leitura real de arquivos do FinGuard, não há análise visual real e não há endpoint de QA no código hoje.

## Documentação de fechamento (01E)

O fechamento da frente `PEDROCORE-REPLAN-01` está consolidado em `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`: escopo executado (01A–01E), commits da frente, transição de visão do projeto, o que existe hoje no código, o que ainda não existe, documentos oficiais criados, relação com o FinGuard, decisões arquiteturais consolidadas, riscos remanescentes, pendências pós-reformulação e a próxima fase recomendada (`PEDROCORE-IMPLEMENT-01`).

Documentação legada/duplicada em `docs/` **não foi removida** nesta etapa — permanece registrada como pendência pós-reformulação, a ser tratada em uma frente futura específica de saneamento documental.
