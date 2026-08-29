# PedroCore — Current Architecture Baseline

Auditoria factual executada em 29/08/2026, antes de qualquer reorganização.
Fonte de verdade: **código real** em `apps/api` e `apps/web`. Documentação
antiga foi usada apenas como hipótese a confrontar, nunca como evidência.

Documentos irmãos desta frente:
[[PEDROCORE_CONTROL_PLANE_MIGRATION_MAP]] e
[[ADR_PEDROCORE_AI_RUNTIME_LEARNING_CONTROL_PLANE]].
Contexto arquitetural anterior: [[MOC_ARQUITETURA]] e
[[00_MAPEAMENTO_GERAL_PEDROCORE]].

## 1. Estado Git no início da auditoria

- branch: `main`
- HEAD: `7fc650c0492dedf3047e5bf3ba98909e2e71a2e1`
- working tree: **limpo** (zero arquivos modificados, zero untracked, zero stash)
- remotes: `origin` → `github.com/pedrofavarobelini/pedrocore.git` (fetch e push)
- branches locais: `main`, `checkpoint/pgd-baseline-2026-08-22`, `fix/portable-uv-lock`

Nenhuma alteração local anterior existia. Nada foi descartado, nenhum
`reset --hard`, `clean -fd`, force push ou rebase destrutivo foi executado.

## 2. Estrutura real do repositório

O repositório **não** possui `packages/`, `modules/`, `scripts/`, `infra/` nem
`.github/` na raiz. A estrutura real é:

```text
pedrocore-ia/
├── apps/
│   ├── api/          backend FastAPI (Python 3.11–3.14)
│   │   ├── app/core/        configuração
│   │   ├── app/modules/     40 módulos de domínio
│   │   ├── migrations/      5 arquivos .sql versionados
│   │   └── tests/           79 arquivos de teste
│   └── web/          frontend React + TypeScript + Vite
├── PedroCore IA/     vault documental Obsidian canônico (155 documentos)
├── README.md
└── VERSION.md
```

Inventário de arquivos rastreados: 247 `.py`, 159 `.md`, 14 `.tsx`, 6 `.ts`,
5 `.sql`. Manifests: `apps/api/pyproject.toml` e `apps/web/package.json`.
Não há Docker, CI declarada, Makefile nem Alembic — as migrations são SQL
plano aplicado por `python -m app.modules.report_memory.migrate`.

**Modular monolith de verdade:** um único processo FastAPI, um único
`pyproject.toml`, 40 módulos separados por pasta e acoplados por import
direto `app.modules.<nome>`. Não existem microsserviços, nem fila, nem
mensageria.

## 3. Superfície pública real

37 paths expostos no OpenAPI (verificado carregando `app.main:app`, não lendo
documentação):

| Grupo | Paths |
|---|---|
| Infra | `GET /`, `GET /health` |
| Assistant | `POST /api/chat`, `GET /api/providers` |
| Orquestração | `POST /api/orchestrate` |
| Report Memory | `POST /api/reports/analyze`, `POST /api/reports/ingest`, `POST /api/reports/v2/analyze`, `POST /api/reports/v2/ingest`, `GET+DELETE /api/project-memory/{project_id}...` (3) |
| Interaction Outcomes | `POST /api/interaction-outcomes`, `GET+DELETE /api/interaction-outcomes/{project_id}` |
| Operational Memory | `POST /api/operational-memory/candidates`, `POST /api/operational-memory/retrieve`, `GET+DELETE /api/operational-memory/{project_id}` |
| Risk Engine | 8 paths sob `/api/risk/...` |
| Safe Reuse | `POST /api/safe-reuse/evaluate` |
| Observability | 4 paths sob `/api/observability/...` |
| Training Candidate | 7 paths sob `/api/training-candidates/...` |

`/api/operational-memory/retrieve` é servido pelo módulo `retrieval`, não pelo
módulo `operational_memory` — o path não revela o módulo dono.

## 4. Runtime Plane existente — auditoria por componente

| Componente | Módulo real | Status | Nota |
|---|---|---|---|
| Orchestration | `orchestration` (2.909 loc) | **IMPLEMENTED** | pipeline central; maior módulo do sistema |
| Assistant/chat | `chat` | **IMPLEMENTED** | `/api/chat` + `/api/providers` |
| Provider registry | `providers/registry.py` | **IMPLEMENTED** | |
| Gemini | `providers/gemini_provider.py` | **IMPLEMENTED** | único homologado para real |
| OpenAI/GPT | `providers/openai_provider.py` | **IMPLEMENTED** | default-off |
| Claude | `providers/claude_provider.py` | **IMPLEMENTED** | default-off |
| Grok | `providers/grok_provider.py` | **IMPLEMENTED** | default-off |
| DeepSeek | `providers/deepseek_provider.py` | **IMPLEMENTED** | default-off |
| Mock | `providers/mock_provider.py` | **IMPLEMENTED** | default do sistema |
| Modelo local | `providers/local_model_provider.py` | **IMPLEMENTED** | opt-in, backend do operador |
| Provider selection | `shadow_routing`, `provider_binding`, `provider_catalog`, `provider_authorization` | **IMPLEMENTED** | modo `legacy` por default |
| Fallback | `provider_health` + `orchestration` | **IMPLEMENTED** | `PEDROCORE_REAL_FALLBACK_ENABLED=false` |
| Retrieval | `retrieval` | **IMPLEMENTED** | |
| Operational Memory | `operational_memory` (1.475 loc) | **IMPLEMENTED** | com repository PostgreSQL |
| Report Intelligence | `report_intelligence` + `report_memory` | **IMPLEMENTED** | v1 e v2 |
| Interaction Outcomes | `interaction_outcomes` | **IMPLEMENTED** | com repository PostgreSQL |
| Safe Reuse | `safe_reuse` | **IMPLEMENTED** | |
| Risk Engine | `risk_engine` (2.504 loc, 14 arquivos) | **IMPLEMENTED** | pre/post execution, historical, contracts |
| Execution Contracts | `risk_engine/execution_contract_*.py` | **IMPLEMENTED** | assinatura obrigatória |
| Frontend | `apps/web` | **IMPLEMENTED** | chat + observability |
| APIs públicas | `app/main.py` | **IMPLEMENTED** | 10 routers, prefixo `/api` |

Nada foi encontrado como `NOT_FOUND` ou `DEPRECATED` no Runtime Plane.

## 5. Learning Plane existente — auditoria por componente

| Componente | Localização real | Status |
|---|---|---|
| `training_data` | `app/modules/training_data/` (2.642 loc, 9 arquivos) | **IMPLEMENTED** |
| Dataset Foundation | `training_data/service.py::DatasetFoundationService` | **IMPLEMENTED** |
| TrainingExampleCandidate | `training_data/schemas.py` | **IMPLEMENTED** |
| TrainingCandidateRecord | `training_data/schemas.py` | **IMPLEMENTED** |
| TrainingSourceSelection | `training_data/router.py` → `/api/training-candidates/select` | **IMPLEMENTED** |
| Candidate Store | `training_data/repository.py` | **IMPLEMENTED** (default OFF, fail-closed) |
| Dataset Readiness | `training_data/acquisition.py::readiness` | **IMPLEMENTED** (`dataset-readiness-v2`) |
| Eligibility | `training_data/policy.py::TrainingEligibilityPolicy` | **IMPLEMENTED** |
| Privacy | `training_data/privacy.py::scan_payload` | **IMPLEMENTED** |
| Provenance | `TrainingEvidenceReference` + códigos de rejeição | **IMPLEMENTED** |
| Authorization | `DataUseAuthorization` | **IMPLEMENTED** |
| Lifecycle | `CandidateLifecycle` (6 estados) | **IMPLEMENTED** |
| Fingerprints | `fingerprint` + `source_reference_hash` (`sha256:`) | **IMPLEMENTED** |
| Quality signals | `CandidateQualitySignals` | **IMPLEMENTED** |
| Human feedback | fonte `human_feedback` + `explicitly_provided` | **IMPLEMENTED** |
| Risk metadata | obrigatória para `risk_analysis` e `execution_outcome` | **IMPLEMENTED** |
| Adapters | `training_data/adapters.py` | **IMPLEMENTED** |
| Persistência PostgreSQL | `training_data/repository.py` (psycopg 3) | **IMPLEMENTED** |
| Migrations | `migrations/0005_training_candidates.sql` | **IMPLEMENTED** |

### `automatic_collection = false` — confirmado e reforçado por tipo

A garantia continua existindo, e é mais forte do que uma flag booleana:

- `training_data/acquisition.py:129` → `automatic_collection = False`
- `training_data/adapters.py:343` → `automatic_collection = False`
- `training_data/schemas.py:400` → `automatic_collection: Literal[False] = False`
- `training_data/schemas.py:389` → `automatic_collection_performed: Literal[False] = False`

`Literal[False]` significa que o Pydantic **rejeita** qualquer tentativa de
construir o objeto com `True`. Não existe configuração, variável de ambiente
ou payload capaz de ligar coleta automática: seria necessário alterar o tipo
no código-fonte. Coberto por `test_dataset_foundation.py` e
`test_training_candidate_acquisition.py`.

## 6. Fontes de training realmente existentes

Confirmadas em `TrainingSourceType` (`training_data/schemas.py`) e mapeadas em
`_SOURCE_DEFINITIONS` (`training_data/service.py`). Oito, não sete:

| Fonte | Entidade | Módulo produtor |
|---|---|---|
| `interaction_outcome` | `InteractionOutcome` | `interaction_outcomes` |
| `operational_pattern` | `OperationalMemoryEntry` | `operational_memory` |
| `report_intelligence_v2` | `IntelligenceReportEnvelopeV2` | `report_intelligence` |
| `qa_evidence` | `QaEvidencePayload` | `report_intelligence` |
| `risk_analysis` | `PreExecutionRiskAnalysis` | `risk_engine` |
| `execution_outcome` | `PostExecutionOutcome` | `risk_engine` |
| `human_feedback` | `HumanFeedback` | `training_data` |
| `elyra_report_snapshot` | `ElyraLearningExport` | `elyra_learning` |

As sete primeiras são as historicamente esperadas. A oitava,
`elyra_report_snapshot`, é adição real e recente (commits `29bb5d2`,
`ac24762`, `8d4406e`, `7fc650c`) e está registrada em
`EXTERNALLY_SUBMITTED_SOURCE_TYPES`: nunca é coletada por adapter interno,
só existe quando um consumer externo autorizado a submete. A distinção é de
segurança — um adapter interno exigiria que o PedroCore alcançasse a base do
consumer, que é exatamente o que a fronteira proíbe.

## 7. Purposes reais

`TrainingPurpose` contém exatamente os quatro esperados: `generative_sft`,
`preference`, `risk`, `evaluation_only`. Nenhum a mais.

A matriz `_PURPOSES_BY_SOURCE` (`training_data/policy.py`) restringe quais
purposes cada fonte admite. `elyra_report_snapshot` admite **somente**
`evaluation_only`; pedir `generative_sft` a partir dela produz
`SOURCE_PURPOSE_MISMATCH` e o candidato é recusado.

## 8. Dataset Readiness observado

Observado sem criar dados, sem alterar métricas e sem executar treinamento.

Com a configuração real do ambiente (persistência default `off`), o Candidate
Store está **desabilitado e fail-closed**:

```text
ReportMemoryRepositoryConfigurationError:
Candidate Store desabilitado; nenhum fallback foi aplicado.
```

Recusar-se a responder é o comportamento correto: um fallback silencioso para
memória faria uma auditoria de readiness ler um store vazio como se fosse o
store real.

Em processo isolado e efêmero (`PEDROCORE_REPORT_MEMORY_PERSISTENCE=memory`,
sem banco, sem escrita em disco), o resultado observado foi:

```text
readiness: DATASET_NOT_READY
policy_version: dataset-readiness-v2
minimum_authorized_candidates: None
canonical_dataset_created: False
training_started: False
blockers: INSUFFICIENT_KNOWN_OUTCOMES, INSUFFICIENT_PURPOSE_COVERAGE,
          INSUFFICIENT_QA_COVERAGE, INSUFFICIENT_SOURCE_DIVERSITY,
          INSUFFICIENT_TASK_DIVERSITY, INSUFFICIENT_VERIFIED_PROVENANCE,
          READINESS_VOLUME_POLICY_NOT_CONFIGURED
```

`DATASET_NOT_READY` **continua sendo o comportamento correto e esperado**.
`READINESS_VOLUME_POLICY_NOT_CONFIGURED` é especialmente importante: sem
`PEDROCORE_DATASET_READINESS_MIN_AUTHORIZED` definido por governança, a
readiness nunca é inferida por contagem. Isto confirma o estado descrito em
[[DATASET_READINESS_AUDIT]].

## 9. Banco e migrations

Cinco migrations SQL versionadas, aplicadas explicitamente:

| Arquivo | Conteúdo |
|---|---|
| `0001_operational_reports.sql` | Report Memory |
| `0002_interaction_outcomes.sql` | Interaction Outcomes |
| `0003_operational_memory.sql` | Operational Memory |
| `0004_operational_memory_retrieval.sql` | índices de retrieval |
| `0005_training_candidates.sql` | Candidate Store |

Quatro repositories PostgreSQL (psycopg 3): `report_memory`,
`interaction_outcomes`, `operational_memory`, `training_data`.

`0005` demonstra o padrão de isolamento: `PRIMARY KEY (project_id,
candidate_id)`, `UNIQUE (project_id, source_type, source_reference_hash,
fingerprint, training_purpose)`, quatro `CHECK` constraints alinhadas aos
enums Pydantic, e dois índices compostos sempre prefixados por `project_id`.
**Isolamento de projeto é chave primária, não filtro de aplicação.**

Modos de persistência: `off` (default) | `memory` | `local_json` |
`postgresql`. Candidates nunca usam `local_json`.

Nenhum banco real foi tocado. Nenhum dado foi criado, alterado ou apagado.

## 10. Testes — baseline antes da reorganização

Comando: `.venv/Scripts/python.exe -m pytest -q --durations=10`
(diretório `apps/api`, Python 3.13.9, pytest 9.1.1, FastAPI 0.138.0)

```text
1085 passed, 21 skipped, 2 warnings in 38.56s
```

- **0 falhas.** Nenhum `PRE_EXISTING_FAILURE`, nenhum `NEW_FAILURE`.
- 21 skips, todos `ENVIRONMENT_BLOCKER` **declarados e intencionais**:
  - 13 exigem `PEDROCORE_TEST_POSTGRES_URL` (PostgreSQL de teste ausente);
  - 8 são opt-in de recursos reais (`PEDROCORE_RUN_REAL_*`), todos default
    `false` por segurança.
- 2 warnings, ambos de deprecação de terceiros e preexistentes:
  `PydanticDeprecatedSince20` em `app/core/config.py:4` (`class Config`) e
  `StarletteDeprecationWarning` sobre `httpx` no `TestClient`.

Lint: `ruff check .` → **All checks passed!**

Grafo documental: 155 documentos, 822 links resolvidos, **zero violações**.

## 11. Documentation Drift identificado

**DOCUMENTATION_DRIFT — 4 ocorrências.**

1. **`MOC_ARQUITETURA` lista 8 endpoints; o código expõe 37.**
   Faltam Interaction Outcomes, Operational Memory, Retrieval, Risk Engine,
   Safe Reuse, Observability, Training Candidate e Reports v2. O documento
   descreve o sistema de várias versões atrás.

2. **`STATUS_ATUAL` (pasta `09-status/`) é status legado da V2** e afirma que
   os endpoints atuais são apenas `/`, `/health`, `/api/chat`,
   `/api/providers`, `/api/orchestrate`. O próprio documento se autodeclara
   legado por nota DOCFIX, mas o texto stale permanece. O status oficial é
   [[09_STATUS_ATUAL]].

3. **Contagens de teste desatualizadas em três documentos.** Baseline real:
   `1085 passed, 21 skipped`. Documentado: `924 passed, 7 skipped`
   ([[DATASET_READINESS_AUDIT]]), `959 passed, 21 skipped`
   ([[09_STATUS_ATUAL]] e `VERSION.md` na raiz do repositório), `751 passed, 7 skipped` (frente
   Structa). São marcos históricos legítimos, mas nenhum documento diz qual é
   o número corrente.

4. **A fonte `elyra_report_snapshot` não aparece em
   [[DATASET_FOUNDATION]].** O documento descreve sete fontes; o código tem
   oito. A oitava é a mais recente e a de regras mais restritas.

Nenhum drift encontrado inverteu uma garantia de segurança: em todos os casos
o código é **mais** restritivo ou mais completo que o documento, nunca menos.

## 12. Segurança

Varredura por `.env`, credenciais hardcoded, API keys, tokens, private keys,
passwords, paths pessoais e dados privados versionados. **Nenhum segredo real
foi encontrado.** Nenhum valor secreto é reproduzido aqui.

- Único arquivo de ambiente rastreado: `apps/api/.env.example`, com todos os
  campos de chave **vazios** (`GEMINI_API_KEY=""`, etc.) e comentários
  explícitos de "nunca versionar o valor real".
- `.gitignore` cobre `.env`, `.env.*` (com exceção de `.env.example`),
  `.venv/`, e — relevante para as próximas Eras — artefatos neurais:
  `*.safetensors`, `*.ckpt`, `pytorch_model*.bin`, `adapter_model*.bin`,
  `/apps/api/training-runs/`, `/apps/api/checkpoints/`,
  `/apps/api/datasets/private/`, `/apps/api/datasets/raw/`.
- Ocorrências textuais de `API_KEY` em `caller_identity/service.py` são o
  **nome** de uma variável de ambiente, não um valor.
- Ocorrências em 6 arquivos de teste são fixtures descritivas
  (`historical-ris…`, `retrieval-alph…`, `safe-reuse-key…`), não credenciais.
- Postura de segurança default: mock por default, providers reais default-off,
  observabilidade off, artifact reader off, OCR/multimodal/Playwright off,
  circuit breaker off, fallback real off, persistência off, routing `legacy`,
  `PEDROCORE_ENFORCE_PROJECT_POLICY=true`. **Fail-closed é o default.**

Observação de higiene (não é vulnerabilidade): a chave global
`PEDROCORE_INTERNAL_API_KEY` apenas *autentica*; ela não prova projeto, e o
caller resultante recebe identidade `ambiguous` sem acesso a provider real.
O design já trata isso corretamente.

## 13. Problemas encontrados

| # | Problema | Severidade | Onde |
|---|---|---|---|
| P1 | Direção de dependência invertida: Runtime importa Learning | **Alta (arquitetural)** | `orchestration/service.py:58` |
| P2 | Acoplamento de projeto no core genérico | **Média** | `orchestration/service.py:380`, `prompt_builder/service.py:25` |
| P3 | Fronteira Runtime × Learning existe só como convenção | **Média** | ausência de declaração e de teste |
| P4 | `DOCUMENTATION_DRIFT` (4 ocorrências) | Baixa | seção 11 |
| P5 | `class Config` do Pydantic v1 deprecado | Baixa | `app/core/config.py:4` |

### P1 em detalhe

`orchestration/service.py` importa `training_candidate_service` e
`TrainingCandidateTransitionError` **no topo do módulo**. O uso é legítimo e
estreito — apenas `_elyra_learning_outcome`, que atende o `task_type` de
submissão/revogação governada e nunca toca provider. Mas o import de topo faz
com que **qualquer** falha de importação do Learning Plane derrube a
importação do Runtime Plane inteiro.

O invariante alvo ("se o Learning Plane falhar, o Assistant ainda deve
funcionar") **já vale em tempo de execução** — a suíte inteira passa com o
Candidate Store desabilitado. Ele **não vale em tempo de importação**.

### P2 em detalhe

Duas comparações literais de projeto dentro de módulos genéricos:

- `orchestration/service.py:380` — `caller.project_id == "elyra"` como uma das
  condições de deduplicação idempotente;
- `prompt_builder/service.py:25` — `data.project.project_id == "finguard"`
  para anexar uma regra de segurança textual.

Os módulos `elyra_textual`, `elyra_multimodal` e `elyra_learning` são
categoria diferente: são *capability modules* de consumer, deliberadamente
nomeados, e não constituem o mesmo problema.

Este ciclo **não corrige P2**: a migração de FinGuard, Structa e Elyra está
explicitamente fora de escopo. P2 fica registrado como dívida técnica com
localização exata em [[PEDROCORE_CONTROL_PLANE_MIGRATION_MAP]].

## 14. Gate Era 1

| Critério | Resultado |
|---|---|
| Estado Git conhecido | OK — branch, HEAD, tree limpo, remotes |
| Estrutura conhecida | OK — 40 módulos, 37 paths, 5 migrations, 79 arquivos de teste |
| Runtime Plane mapeado | OK — 21 componentes, todos IMPLEMENTED |
| Learning Plane mapeado | OK — 19 componentes, todos IMPLEMENTED |
| Dataset Foundation encontrada | OK — `training_data`, 2.642 loc |
| Testes baseline executados | OK — 1085 passed, 21 skipped, 0 failed |
| Drifts identificados | OK — 4 registrados |
| Migration map produzido | OK |
| ADR criada | OK |
| Nenhum dado destruído | OK |

```text
ERA_1_PASS
```

O estado encontrado **não** contradiz o plano: ele o confirma e o supera. O
Learning Plane não precisou ser criado — ele já existe, é substancial e é
governado. A Era 2 é portanto uma formalização de fronteira, não uma
construção.
