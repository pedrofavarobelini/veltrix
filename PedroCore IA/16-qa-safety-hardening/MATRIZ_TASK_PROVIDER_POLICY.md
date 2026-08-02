# Matriz task_type × provider × policy

Fonte de verdade no código: `app/modules/task_router/service.py` (strategies),
`app/modules/providers/registry.py` (providers) e
`app/modules/policy_enforcement/service.py` (bloqueio real).

## Providers

| Provider | Tipo | `real_provider` | Precisa de chave | Default |
|---|---|---|---|---|
| `mock` | Simulado | não | não | permitido sempre |
| `local_qa` | Determinístico de QA (pseudo-provider) | não | não | permitido sempre; único confiável para release gate |
| `local_model` | Generativo local opt-in (contrato pronto, transport ausente) | não | não | bloqueado sem `allow_local_model=true` + `PEDROCORE_ENABLE_LOCAL_MODEL=true` + backend válido |
| `gemini`, `openai`, `claude`, `deepseek`, `grok` | Reais | sim | sim | **bloqueados** (`allow_real_provider=false` default) |
| inválido/desconhecido | — | — | — | fallback mock controlado (`Fallback acionado`) |

## task_types conhecidos

| task_type | Criticidade | `allow_mock` | Observações |
|---|---|---|---|
| `general_chat`, `technical_explanation` | low | sim | — |
| `code_help`, `artifact_summary` | medium | sim | — |
| `qa_report_analysis`, `qa_failure_diagnosis` | high | não | análise QA local obrigatória |
| `release_gate_review` | critical | não | só `local_qa` aprova; provider real/mock/local_model bloqueiam avanço |
| `exploratory_test_plan`, `manual_exploration_report` | medium | sim | somente plano; sem execução |
| `assisted_exploration_review` | high | sim | — |
| `report_ingestion`, `project_memory_summary`, `report_memory_query` | medium | sim | sempre com warning `REPORT_MEMORY_IS_NOT_TRAINING` |
| `model_foundation_review`, `intelligence_planning`, `evaluation_run` | medium | sim | — |
| `assistant_chat`, `ecosystem_assistant`, `local_model_chat` | low | sim | read-only |
| `finance_advice` | medium | sim | disclaimer obrigatório (`FINANCIAL_DISCLAIMER`) |
| `project_status` | medium | sim | — |
| desconhecido | low | sim | tratado como `unknown` + warning `UNKNOWN_TASK_TYPE` |

## Policy (bloqueio real, antes de qualquer provider)

| Condição | Resultado |
|---|---|
| task_type com semântica de execução/escrita/deleção (`execute`, `delete`, `drop`, `deploy`, …) | `blocked` + `PROJECT_POLICY_BLOCKED`; **independe** de `PEDROCORE_ENFORCE_PROJECT_POLICY` |
| metadata/context com chave perigosa (`command`, `shell`, `exec`, …) | `blocked` + `PROJECT_POLICY_BLOCKED` |
| fluxo crítico com task não permitida para o projeto | `blocked` (`FINGUARD_TASK_NOT_ALLOWED` para FinGuard) |
| origem desconhecida em fluxo crítico | `blocked` + `PROJECT_POLICY_BLOCKED` |
| bloqueio de policy | `provider_used="none"`, `model="none"`; nenhum provider (nem mock) é tocado |

## Flags obrigatórias e defaults

| Flag | Default | Efeito |
|---|---|---|
| `allow_real_provider` (payload) | `false` | provider real → fallback mock + `PROVIDER_REAL_BLOCKED` |
| `allow_local_model` (payload) | `false` | local_model → fallback mock + `LOCAL_MODEL_NOT_AUTHORIZED` |
| `context_from_memory` (payload) | `false` | memória técnica nunca entra no prompt |
| `PEDROCORE_REPORT_MEMORY_PERSISTENCE` | `off` | ingest não guarda nada (`stored=false`); valor inválido = `off` |
| `PEDROCORE_ENABLE_LOCAL_MODEL` | `false` | local_model `configured=false` |
| `PEDROCORE_ENFORCE_PROJECT_POLICY` | `true` | única flag default-true (segurança por padrão) |

## Comportamento esperado (resumo verificável)

- Payload aninhado (`context`/`metadata`/campo extra) **não** ativa provider real.
- Falha de policy **nunca** executa provider (provado por spy no registry).
- `finance_advice` sempre anexa o disclaimer, inclusive em fallback.
- Release gate só avança com `local_qa` + evidência textual limpa.

Testes que fixam esta matriz: `test_provider_real_safety.py`,
`test_policy_negative_cases.py`, `test_orchestrate_contract_safety.py`,
`test_eval_harness_extended.py`.

## Links relacionados

- [[../MOC_QA_SAFETY_HARDENING]]
- [[RELEASE_GATE_CHECKLIST]]
- [[PROVIDER_REAL_SAFETY]]
- [[../MOC_QA_RELEASE_GATE]]
- [[../00_MAPEAMENTO_GERAL_PEDROCORE]]
