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
- **01B — Planejamento técnico e contratos.** *(em andamento)* Especifica, em `docs/10-contratos/`, os contratos de request/response para consumo por sistemas externos (`origin_system`, `task_type`, `context`, `artifacts`), tipos de tarefa, resposta estruturada, contrato de artefatos, roteamento de provider e regras de fallback — ainda sem implementar código.
- **01C — Arquitetura-alvo: Task Router, Prompt Builder, Project Context.** *(planejado)* Desenhar os módulos responsáveis por classificar a solicitação, montar o prompt final e resolver contexto por projeto/sistema de origem.
- **01D — Planejamento de QA Intelligence.** *(planejado)* Desenhar, sem implementar, o caso de uso de leitura e análise de relatórios de QA (Markdown livre) de projetos externos como o FinGuard, sempre em modo somente leitura.
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

Os contratos técnicos planejados nesta fase estão detalhados em `docs/10-contratos/`:

- `docs/10-contratos/CONTRATOS_TECNICOS_PEDROCORE.md` — índice e princípios gerais.
- `docs/10-contratos/CONTRATO_ORQUESTRACAO.md` — contrato de entrada/saída, tipos de tarefa, artefatos, provider preference e fallback.
- `docs/10-contratos/CONTRATO_QA_INTELLIGENCE.md` — resposta estruturada de QA e limites com o FinGuard.

Esses documentos são especificação/planejamento. Nenhum contrato neles descrito está implementado no código.
