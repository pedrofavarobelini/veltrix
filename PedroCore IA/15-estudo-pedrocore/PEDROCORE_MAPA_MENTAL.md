# PedroCore - Mapa Mental

Atualizado em: 09/07/2026

## Visao geral

- PedroCore IA
  - Core/orquestrador local de IA.
  - Servico central para projetos consumidores.
  - Nao e modelo treinado.
  - Nao faz fine-tuning.
  - Nao substitui validacao humana.

## Arquitetura

- API FastAPI
  - `GET /`
  - `GET /health`
  - `POST /api/chat`
  - `GET /api/providers`
  - `POST /api/orchestrate`
  - `POST /api/reports/analyze`
  - `POST /api/reports/ingest`
  - `GET /api/project-memory/{project_id}/summary`
- Pipeline principal
  - ChatRequest
  - Task Router
  - Project Context
  - Policy Enforcement
  - Intelligence Layer
  - Report Memory opcional
  - Artifact Reader opcional
  - Artifacts Service
  - Prompt Builder
  - Provider Registry
  - QA Text Analyzer
  - QA Response / Release Gate
  - Visual QA / Exploration quando aplicavel
  - Audit
  - Response

## Modulos

- `chat`: compatibilidade com `/api/chat`.
- `orchestration`: pipeline central.
- `task_router`: classifica `task_type`.
- `project_context`: resolve limites por `origin_system`.
- `policy_enforcement`: bloqueia comando, escrita, delecao, deploy, push e task critica indevida.
- `prompt_builder`: monta prompt enriquecido.
- `providers`: registry, mock e providers reais.
- `intelligence_layer`: plano deterministico antes do provider.
- `report_intelligence`: extrai sinais de relatorios.
- `report_memory`: memoria tecnica controlada, default off.
- `evaluation`: checks de seguranca/coerencia.
- `eval_harness`: fixtures deterministicas.
- `artifacts`: processa payload textual.
- `artifact_reader`: leitura por path opt-in e allowlisted.
- `qa_analysis`: heuristica textual local.
- `qa_response`: skeleton QA e release gate.
- `visual_qa`: stub/guard seguro.
- `exploration`: plano assistido, sem acao autonoma.
- `audit`: metadados de auditoria nao persistentes.

## Providers

- `mock`: seguro, local, default/fallback.
- `local_qa`: deterministico, interno, usado em QA/release gate.
- `local_model`: generativo local futuro, registrado default-off, sem transport real.
- `gemini`, `openai`, `claude`, `deepseek`, `grok`: reais/externos, bloqueados por default.

## Seguranca

- `allow_real_provider=false` por default.
- `allow_local_model=false` por default.
- `context_from_memory=false` por default.
- Report Memory default off.
- Artifact Reader default off.
- Recursos reais opt-in e revisao humana.
- `.env` nao deve ser lido, exposto, commitado ou stageado.
- FinGuard permanece read-only como consumidor.

## Memoria

- Relatorios viram sinais.
- Sinais podem virar snapshot tecnico.
- Snapshot pode virar contexto quando `context_from_memory=true`.
- Nada disso treina pesos.
- Nada disso e fine-tuning.
- Nada disso e RAG.

## Local model

- `local_model` nao e `local_qa`.
- `local_qa` e heuristica deterministica.
- `local_model` seria LLM local generativo.
- Hoje: registrado, bloqueado por default, sem transport real.
- Futuro: backend local manual, flags, teste real opt-in.

## Eval harness

- Mede invariantes.
- Nao mede qualidade de LLM.
- Nao chama provider real.
- Nao chama rede.
- Nao depende de modelo local.

## Integracao futura com FinGuard

- Hoje: PedroCore aceita `origin_system=finguard` como consumidor read-only.
- Hoje: FinGuard nao foi lido nem alterado.
- Futuro: cliente HTTP/assistente FinGuard em frente separada.
- Regra: frontend do consumidor deve chamar seu backend; backend chama PedroCore.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[../MOC_PEDROCORE_IA]]
- [[PEDROCORE_FLUXO_COMPLETO]]
- [[../MOC_ARQUITETURA]]
- [[../MOC_SEGURANCA]]
