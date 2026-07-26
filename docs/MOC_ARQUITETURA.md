# MOC Arquitetura

Mapa de arquitetura atual e historico de planejamento.

## Estado atual

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - secoes 5 a 8 documentam arquitetura, endpoints, modulos e fluxo `/api/orchestrate`.
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]] - fechamento final do core operacional seguro.
- [[10-api/EXEMPLOS_API_MVP]] - exemplos seguros de `/api/chat` e `/api/orchestrate`.
- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]] - visão integrada da arquitetura multi-provider atual.
- [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]] - pipeline normal, timeout ambíguo e fallback seguro.

## Endpoints

- `GET /` - `apps/api/app/main.py`
- `GET /health` - `apps/api/app/main.py`
- `POST /api/chat` - `apps/api/app/modules/chat/router.py`
- `GET /api/providers` - `apps/api/app/modules/chat/router.py`
- `POST /api/orchestrate` - `apps/api/app/modules/orchestration/router.py`
- `POST /api/reports/analyze` - `apps/api/app/modules/report_memory/router.py`
- `POST /api/reports/ingest` - `apps/api/app/modules/report_memory/router.py`
- `GET /api/project-memory/{project_id}/summary` - `apps/api/app/modules/report_memory/router.py`

## Estudo arquitetural

- [[15-estudo-pedrocore/PEDROCORE_FLUXO_COMPLETO]] - fluxo ponta a ponta do consumidor ate resposta/audit.
- [[15-estudo-pedrocore/PEDROCORE_MAPA_MENTAL]] - mapa mental de modulos, rotas, providers e seguranca.
- [[15-estudo-pedrocore/PEDROCORE_AUDITORIA_STUDY_MAP_01]] - validacao local da arquitetura atual.

## Modulos backend

- `chat` - compatibilidade de `/api/chat`.
- `providers` - registry, mock e providers reais.
- `caller_identity` - identidade confiável, papel, ambiente e projeto.
- `provider_catalog` - catálogo estático de providers e modelos.
- `provider_authorization` - matriz fail-closed por identidade/projeto.
- `provider_binding` - binding total entre provider e modelo.
- `shadow_routing` - candidatos e eliminações sem executar provider.
- `provider_health` - circuit breaker local, monotônico e default-off.
- `orchestration` - pipeline central.
- `task_router` - estrategias por `task_type`.
- `project_context` - contexto por `origin_system`.
- `policy_enforcement` - bloqueios fortes.
- `prompt_builder` - prompt enriquecido.
- `artifacts` - artefatos por payload.
- `artifact_reader` - leitura opt-in allowlisted.
- `qa_analysis` - heuristica textual local.
- `qa_response` - QA skeleton e release gate.
- `visual_qa` - stub visual conservador.
- `ocr` - OCR local opt-in.
- `exploration` - plano manual assistido.
- `exploration/playwright_adapter` - Playwright read-only opt-in.
- `contracts` - warning/error codes.
- `audit` - audit nao persistente.
- `real_features` - flags de recursos reais.
- `intelligence_layer` - plano cognitivo deterministico interno (MODEL-FOUNDATION-01).
- `report_intelligence` - sinais de relatorios tecnicos, sem persistencia (MODEL-FOUNDATION-01).
- `evaluation` - checks deterministicos de seguranca/coerencia (MODEL-FOUNDATION-01).
- `providers/local_model_contract` - contrato futuro do provider generativo local (MODEL-FOUNDATION-01).
- `report_memory` - memoria tecnica controlada + rotas de relatorios (ECOSYSTEM-SUITE-01).
- `providers/local_model_provider` - provider generativo local opt-in, sem rede (ECOSYSTEM-SUITE-01).
- `eval_harness` - harness deterministico de avaliacao (ECOSYSTEM-SUITE-01).

## Fundação de inteligência própria

- [[14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]]
- [[14-intelligence-layer/REPORT_INTELLIGENCE_FOUNDATION]]
- [[14-intelligence-layer/LOCAL_MODEL_PROVIDER_CONTRACT]]
- [[14-intelligence-layer/EVALUATION_FOUNDATION]]

## Planejamento historico

Estes documentos nasceram como planejamento e devem ser lidos junto do estado atual em [[00_MAPEAMENTO_GERAL_PEDROCORE]]:

- [[11-arquitetura-alvo/ARQUITETURA_ALVO_PEDROCORE]]
- [[11-arquitetura-alvo/TASK_ROUTER]]
- [[11-arquitetura-alvo/PROJECT_CONTEXT]]
- [[11-arquitetura-alvo/PROMPT_BUILDER]]
- [[10-contratos/CONTRATOS_TECNICOS_PEDROCORE]]
- [[10-contratos/CONTRATO_ORQUESTRACAO]]
