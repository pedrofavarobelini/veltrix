# MOC Arquitetura

Mapa de arquitetura atual e historico de planejamento.

## Estado atual

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - secoes 5 a 8 documentam arquitetura, endpoints, modulos e fluxo `/api/orchestrate`.
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]] - fechamento final do core operacional seguro.
- [[10-api/EXEMPLOS_API_MVP]] - exemplos seguros de `/api/chat` e `/api/orchestrate`.

## Endpoints

- `GET /` - `apps/api/app/main.py`
- `GET /health` - `apps/api/app/main.py`
- `POST /api/chat` - `apps/api/app/modules/chat/router.py`
- `GET /api/providers` - `apps/api/app/modules/chat/router.py`
- `POST /api/orchestrate` - `apps/api/app/modules/orchestration/router.py`

## Modulos backend

- `chat` - compatibilidade de `/api/chat`.
- `providers` - registry, mock e providers reais.
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
