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

- **01A — Consolidação documental e visão oficial.** *(concluída)* Reformulou a documentação principal (README, VERSION, visão geral, objetivo, roadmap, status, decisões técnicas, changelog) para refletir a nova visão estratégica, sem alterar código. Commitada em `1e5a8cb`.
- **01B — Planejamento técnico e contratos.** *(concluída)* Especificou, em `docs/10-contratos/`, os contratos de request/response para consumo por sistemas externos (`origin_system`, `task_type`, `context`, `artifacts`), tipos de tarefa, resposta estruturada, contrato de artefatos, roteamento de provider e regras de fallback — sem implementar código. Commitada em `6e7badd`.
- **01C — Arquitetura-alvo: Task Router, Prompt Builder, Project Context.** *(concluída)* Documentou, em `docs/11-arquitetura-alvo/`, a arquitetura-alvo que sustentaria os contratos da 01B: Task Router, Prompt Builder, Project Context, Provider Orchestration, Structured Responses, Artifact Reader e Audit/logs — sem implementar código. Commitada em `c1e7816`.
- **01D — Planejamento de QA Intelligence.** *(em andamento)* Documenta, em `docs/12-qa-intelligence/`, a camada futura de QA Intelligence: análise de relatórios de QA (Markdown livre), diagnóstico de falhas, release gate assistido, resposta estruturada, severidade/risco e limites de atuação — sempre em modo somente leitura e sem implementar código.
- **01E — Fechamento documental da reformulação.** *(planejado)* Consolidar/remover documentação duplicada ou obsoleta identificada nas fases anteriores.

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
