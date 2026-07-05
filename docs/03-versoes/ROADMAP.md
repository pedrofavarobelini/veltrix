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

- **01C — Project Context mínimo.** *(implementada, commitada)* Commitada em `95cbfab`. Módulo `apps/api/app/modules/project_context/`: `ProjectContextResolver.resolve(origin_system)` resolve configuração interna por sistema (`pedrocore`, `finguard`, `unknown`), com `read_only`, `can_execute_commands`, `can_write_files`, `allowed_tasks`, `warnings` e `notes`. Não lê arquivos externos, não acessa o FinGuard real — apenas devolve dados de configuração interna.

- **01D — Prompt Builder mínimo.** *(implementada, commitada)* Commitada em `95cbfab`. Módulo `apps/api/app/modules/prompt_builder/`: monta `enriched_system_prompt` com seções `[Instruções do sistema]`, `[Tarefa]`, `[Origem]`, `[Limites do projeto]`, `[Contexto enviado]`, `[Metadata]`, `[Regras de segurança]` (com regra adicional quando `origin_system=finguard`). Não chama provider, não decide provider. `BaseAIProvider.build_prompt` continua existindo e intacto; providers reais não foram reescritos.

- **01E — Structured Response metadata.** *(implementada, commitada)* Commitada em `95cbfab`. `ChatResponse` ganhou `project_id`, `project_read_only`, `project_can_execute_commands`, `project_can_write_files`, `response_style`, `audit_id`, `audit_timestamp`, todos com defaults seguros. Campos antigos (incluindo os da 01A/01B) preservados. Campos de QA Intelligence real (`findings`, `failures`, `risk_level`, `can_advance`, `suggested_commands`, `suggested_fixes`) **não** foram adicionados — pertencem a uma fase futura.

- **01F — Audit metadata não persistente.** *(implementada, commitada)* Commitada em `95cbfab`. Módulo `apps/api/app/modules/audit/`: `AuditService.create()` gera `audit_id` (uuid4) e `timestamp` (ISO, UTC) em memória por requisição, sem banco, arquivo, middleware ou endpoint. `fallback_used` é atualizado ao final do fluxo.

- **01G — Testes de integração do fluxo orquestrado.** *(implementada, commitada)* Commitada em `95cbfab`. Novos arquivos `apps/api/tests/test_project_context.py`, `test_prompt_builder.py` e `test_orchestration_flow.py`, cobrindo Project Context, Prompt Builder e o fluxo `/api/chat` de ponta a ponta (request antiga, `origin_system=finguard`, origem desconhecida, fallback crítico com audit, `requires_structured_response`, `/api/providers`). Testes backend: `37 passed, 2 warnings`.

- **01H — Proteção contra provider real em testes.** *(implementada, commitada)* Commitada em `95cbfab`. Teste dedicado garante que o provider default é `mock`, que ele não é `real_provider` e está sempre configurado; toda a suíte usa apenas `mock`/provider inexistente.

- **01I — Orchestration module.** *(avaliada, adiada)* Não foi criado `apps/api/app/modules/orchestration/`. Justificativa: `ChatService.send_message` já encapsula o pipeline completo (Task Router → Project Context → Audit → Prompt Builder → Provider → fallback) em um ponto de entrada único e reutilizável; extrair um módulo de orquestração agora seria abstração prematura sem um segundo consumidor real. Fica registrado como pendência para quando um endpoint `/api/orchestrate` (ainda inexistente) vier a ser criado.

Ainda não existe: Artifact Reader real, QA Intelligence real, análise visual, banco de dados/persistência, autenticação entre sistemas, endpoint `/api/orchestrate`, integração real com o FinGuard, ou qualquer alteração de frontend/design.

## PEDROCORE-IMPLEMENT-02 — QA textual foundation

Segunda frente de implementação de código, evoluindo a base interna de orquestração para suportar policy de tarefas por projeto, artefatos textuais por payload e um skeleton seguro de resposta QA — sem QA Intelligence real, sem leitura de arquivo e sem integração real com o FinGuard.

- **02A — Policy de allowed_tasks por Project Context.** *(implementada, commitada)* Commitada em `e115672`. `TaskPolicyResult`/`evaluate_task_policy(project, task_type)` em `apps/api/app/modules/project_context/`: task listada em `allowed_tasks` → permitida sem warning; task fora da lista → warning de cautela, sem bloquear; lista vazia/projeto `unknown` → permitida com warning específico. `ChatResponse.task_allowed_for_project` adicionado.
- **02B — Artefatos textuais por payload.** *(implementada, commitada)* Commitada em `e115672`. `ChatRequest.artifacts` opcional; módulo `apps/api/app/modules/artifacts/`: `ArtifactService.process()` gera `count`/`types`/`names`/`warnings`/`text_block` a partir do conteúdo enviado, sem ler nenhum arquivo. 9 tipos textuais aceitos; tipos visuais (`screenshot`, `image`, `playwright_trace`) apenas sinalizados como não suportados. `ChatResponse` ganhou `artifact_count`, `artifact_types`, `artifact_warnings`.
- **02C — Prompt Builder com artefatos.** *(implementada, commitada)* Commitada em `e115672`. Nova seção `[Artefatos enviados]` no prompt enriquecido, com o texto recebido no payload; sem interpretação ou resumo automático; informa explicitamente quando nenhum artefato foi enviado.
- **02D — QA response skeleton seguro.** *(implementada, commitada)* Commitada em `e115672`. Módulo `apps/api/app/modules/qa_response/`: `QAResponseSkeleton` retornado apenas para `qa_report_analysis`/`qa_failure_diagnosis`/`release_gate_review`, sempre com `status="not_analyzed"`, `risk_level="unknown"`, `can_advance=False`, `confidence=0.0` e listas de achados vazias — deixando explícito que não há análise real. Tarefas não-QA retornam `qa_skeleton=None`. `ChatResponse.qa_skeleton` adicionado.
- **02E — Warnings específicos para QA textual.** *(implementada, commitada)* Commitada em `e115672`. Tarefa QA crítica sem artefatos gera warning dedicado (em `task_warnings` e no skeleton); fallback crítico continua gerando warning forte, refletido também no skeleton; artefato visual gera warning em `artifact_warnings`/`task_warnings`/skeleton; policy negada gera warning em `task_warnings`.
- **02F — Testes de contrato para fluxo QA textual.** *(implementada, commitada)* Commitada em `e115672`. Novos arquivos `apps/api/tests/test_artifacts.py`, `test_qa_response.py` e `test_qa_flow.py`, mais extensões em `test_project_context.py` e `test_prompt_builder.py`, cobrindo os 19 itens de contrato (artifacts, policy, skeleton, fallback crítico, compatibilidade retroativa). Testes backend: `66 passed, 2 warnings`.
- **02G — Proteção adicional contra provider real em testes.** *(implementada, commitada)* Commitada em `e115672`. Toda a suíte nova usa apenas `mock`/provider inexistente; nenhuma chamada a Gemini/OpenAI/Claude/DeepSeek/Grok.

Ainda não existia ao fim desta frente: Artifact Reader real (leitura automática de arquivo/pasta), QA Intelligence real, análise visual real, endpoint `/api/orchestrate`, integração real com o FinGuard, bloqueio duro por policy de `allowed_tasks`, banco/persistência, autenticação entre sistemas, ou qualquer alteração de frontend/design. (O endpoint `/api/orchestrate` e a análise QA textual local passaram a existir na frente seguinte, `PEDROCORE-IMPLEMENT-03`.)

## PEDROCORE-IMPLEMENT-03 — MVP backend (Blocos 1–7)

Terceira frente de implementação. Status: **implementada, validada e commitada em `6ed4c41`**. Ver `docs/08_CHANGELOG.md` para o detalhamento completo.

- **Bloco 1 — QA textual real inicial.** `QATextAnalyzer` local determinístico (`apps/api/app/modules/qa_analysis/`): detecção de sucesso/falha/erro/warning e risco crítico por heurística textual, `risk_level`, `confidence`, `can_advance` conservador, sugestões seguras. Sem IA externa, sem leitura de arquivo, sem execução de comando. Skeleton QA agora é preenchido de verdade (`analysis_source="local_text_heuristic"`).
- **Bloco 2 — Release Gate conservador.** `evaluate_release_gate` bloqueia sem artifacts, com path rejeitado, truncamento, falha/erro, risco high/critical, fallback Mock, safe mode ou provider mock; só libera com evidência limpa via análise local (`local_qa`) e confiança ≥ 0.6; `blocked_reason` sempre preenchido ao bloquear.
- **Bloco 3 — API operacional mínima.** `OrchestrationService` centraliza o pipeline; novo `POST /api/orchestrate` com resposta estruturada (qa, release_gate, audit completo, warnings com severidade); `POST /api/chat` continua 100% compatível e sem API key.
- **Bloco 4 — Safe mode.** `allow_real_provider=false` por padrão; providers reais nunca são chamados sem autorização explícita; bloqueio gera `PROVIDER_REAL_BLOCKED` + fallback Mock + `safe_mode_blocked=true`.
- **Bloco 5 — Autenticação interna simples.** `PEDROCORE_INTERNAL_API_KEY` opcional + header `X-PedroCore-Api-Key` somente para `/api/orchestrate`; modo dev/local com `INTERNAL_AUTH_NOT_CONFIGURED` quando não configurada.
- **Bloco 6 — Warning/Error contract.** Códigos padronizados com severidade em `apps/api/app/modules/contracts/`; `warning_codes`/`warnings`/`error_code`/`blocked_reason`/`status` nas respostas; `task_warnings` textual mantido por compatibilidade.
- **Bloco 7 — Audit mínimo não persistente.** `AuditMetadata` completo (`provider_used`, `safe_mode_blocked`, `status`, `latency_ms`, `risk_level`, `can_advance`), retornado só na resposta, sem persistência e sem segredos/conteúdo de artifacts.

Limites e artifacts: máx. 10 artefatos, 20k chars por artefato, 100k total; campos de path em metadata são rejeitados sem leitura (`ARTIFACT_PATH_REJECTED`).

Testes backend: `125 passed, 2 warnings` (66 anteriores + 59 novos).

Ainda não existe nesta frente: integração real com o FinGuard, leitura real de arquivos, execução de comandos pelo PedroCore, QA visual real, OCR, Playwright, agente exploratório, dashboard, log persistente, provider real liberado em fluxo crítico, Blocos 7–11 do planejamento maior, Bloco 12 e Blocos 13–15 finais.

## PEDROCORE-FINALIZE-04 — Consolidação documental e tag v6.0.0

Status: **concluída e tagueada em `v6.0.0`**.

Commit documental: `ee2ac68 — docs: consolidar MVP e preparar tag v6`.

Tag anotada: `v6.0.0`, apontando para `ee2ac68679feea6ac108abba8726d11da101576c` (`ee2ac68`), com a mensagem `v6.0.0 - MVP backend PedroCore IA`.

A tag `v6.0.0` representa o fechamento do MVP backend. Ela não representa conclusão do projeto inteiro: Blocos 7–11 do planejamento maior, Bloco 12 e Blocos 13–15 finais permanecem planejados para frentes posteriores.

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
