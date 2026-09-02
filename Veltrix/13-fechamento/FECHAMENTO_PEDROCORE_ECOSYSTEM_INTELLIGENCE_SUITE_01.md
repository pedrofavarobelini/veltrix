# Fechamento — PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01

Atualizado em: 09/07/2026

Links: [[FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01]] | [[../10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT]] | [[../10-contratos/CONTRATO_REPORT_MEMORY]] | [[../14-intelligence-layer/REPORT_MEMORY]] | [[../14-intelligence-layer/LOCAL_MODEL_PROVIDER]] | [[../14-intelligence-layer/EVAL_HARNESS]]

## 1. Objetivo da frente (pacote)

Consolidar quatro trilhas em uma execução: (A) `PEDROCORE-ECOSYSTEM-FINALIZE-01`, (B) `PEDROCORE-REPORT-MEMORY-01`, (C) `PEDROCORE-LOCAL-MODEL-01`, (D) `PEDROCORE-EVAL-HARNESS-01` — sem provider real, sem treinamento/fine-tuning/autoaprendizado e sem mexer no FinGuard.

## 2. Estado inicial verificado

- Branch `main`; HEAD `689e50a` (feat: preparar fundacao de inteligencia propria do Veltrix); working tree limpo.
- Tags: `v7.0.0` → `33b2c04`; `.env` não tracked (apenas `.env.example`).
- Baseline: `257 passed, 6 skipped, 2 warnings`.

## 3. Fase A — Ecosystem finalize (implementado)

- `ChatRequest` ganhou `allow_local_model=false` e `context_from_memory=false` (aditivos).
- 7 task types novos: `assistant_chat`, `ecosystem_assistant`, `finance_advice`, `project_status`, `report_memory_query`, `local_model_chat`, `evaluation_run` — todos para `pedrocore`; FinGuard recebeu apenas `assistant_chat`, `finance_advice`, `project_status`, `report_memory_query` como **consumidor read-only** (sem `general_chat`, sem `report_ingestion`).
- `finance_advice`: disclaimer obrigatório anexado à resposta + warning `FINANCIAL_DISCLAIMER`; read-only; nunca executa ação financeira.
- Intelligence Layer conectada de verdade: `plan.instructions` viram a seção `[Plano de inteligência]` do prompt enriquecido (Prompt Builder com campos opcionais retrocompatíveis).
- `AssistantResponsePayload` + `OrchestrationService.build_assistant_payload()` como projeção documentada para consumidores.
- `OrchestrateResponse` ganhou `memory_used` (aditivo); nenhum campo removido/alterado.
- Contrato: `docs/10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT.md`.

## 4. Fase B — Report Memory (implementado)

- Módulo `report_memory/` (schemas, repository, service, router): `ReportMemoryEntry`, `ReportMemoryQuery`, `ProjectMemorySnapshot`.
- Persistência por flag `PEDROCORE_REPORT_MEMORY_PERSISTENCE` = `off` (default) | `memory` | `local_json` (diretório do operador; testes com tmp_path; segredos redigidos com `[REDACTED]`).
- Rotas novas (mesma auth opcional do orchestrate): `POST /api/reports/analyze` (sem persistir), `POST /api/reports/ingest`, `GET /api/project-memory/{project_id}/summary`.
- Integração `/api/orchestrate`: `context_from_memory=true` anexa snapshot limitado (2k chars) como `[Memória técnica]`, marca `memory_used=true` (`REPORT_MEMORY_USED`/`REPORT_MEMORY_DISABLED`/`REPORT_MEMORY_EMPTY`).
- Tasks de memória sempre emitem `REPORT_MEMORY_IS_NOT_TRAINING`.

## 5. Fase C — Local Model Provider (implementado, sem rede)

- `providers/local_model_provider.py`: `LocalModelProvider` registrado como `local_model` (default OFF, `real_provider=false`, `configured=false` sem flag).
- Gate cumulativo na orquestração: `allow_local_model=true` + `PEDROCORE_ENABLE_LOCAL_MODEL=true` + backend válido + task não crítica/não release gate; senão fallback Mock com `LOCAL_MODEL_NOT_AUTHORIZED`/`LOCAL_MODEL_DISABLED`/`LOCAL_MODEL_TASK_BLOCKED`.
- **Transport padrão é None — nenhuma chamada de rede existe nesta frente**; habilitado sem transport → `LOCAL_MODEL_TRANSPORT_UNAVAILABLE` + fallback. Testes usam fake transport. Transport HTTP real é frente futura.
- `local_model` fora de `RELEASE_GATE_TRUSTED_PROVIDERS` (continua `{"local_qa"}`).
- Flags novas apenas em `.env.example`.

## 6. Fase D — Eval Harness (implementado)

- Módulo `eval_harness/` (schemas, fixtures, service, run): `EvalCase` (rejeita `allow_real_provider=true` por validação), `EvalRunResult`, 11 fixtures determinísticas cobrindo os invariantes exigidos.
- Executor local: `uv run python -m app.modules.eval_harness.run` (JSON + exit code; verificado: 11/11 passed, exit 0). Sem rota pública.

## 7. O que ficou apenas documentado

- Transport HTTP real do `local_model` (backend local é responsabilidade do operador; frente futura).
- Integração do Assistente FinGuard via Veltrix (`FINGUARD-PEDROCORE-ASSISTANT-01` — o FinGuard já possui estrutura de assistente/tela/botão no repositório próprio; a integração via Veltrix não foi implementada nesta frente).
- Benchmark real de LLM (fica para evolução do harness quando houver modelo local funcional).

## 8. Testes

- Novos: `test_ecosystem_contract.py`, `test_report_memory.py`, `test_local_model_provider.py`, `test_eval_harness.py` (39 testes novos).
- Atualizados (retrocompatibilidade intencional, sem redução de segurança): `test_local_model_contract.py` (local_model agora registrado porém disabled) e `test_project_context.py` (lista exata de allowed_tasks do FinGuard ganhou as 4 tasks de consumidor).
- Resultado final: **`296 passed, 6 skipped, 2 warnings`** (baseline 257; skips/warnings pré-existentes; nenhum warning novo).

## 9. Gates de segurança confirmados

- Nenhum provider real chamado; `allow_real_provider=true` não usado.
- `apps/api/.env` não lido/alterado/exposto/stageado; apenas `.env.example` atualizado.
- FinGuard não lido/alterado; nenhuma regra FinGuard-específica que impeça outros consumidores.
- Sem treinamento/fine-tuning/LoRA/autoaprendizado; sem backend instalado; sem modelo baixado; sem rede real em teste.
- `local_model` default-off; `context_from_memory` default-off; report memory default-off e sem segredos.
- Release gate continua confiando somente em `local_qa`; `/api/chat` e `/api/orchestrate` preservados (mudanças apenas aditivas).
- Sem commit/push/tag/merge.

## 10. Riscos e limitações remanescentes

- Snapshot de memória é agregação determinística simples; sem ranking semântico.
- Redação de segredos por regex não é exaustiva — relatórios não devem conter segredos na origem.
- `local_json` grava em disco local do operador; retenção/limpeza é manual.
- Eval harness mede invariantes, não qualidade de geração.

## 11. Roadmap recomendado

1. `FINGUARD-PEDROCORE-ASSISTANT-01` — integração do Assistente FinGuard via Veltrix (lado cliente fora deste repositório).
2. `PEDROCORE-LOCAL-MODEL-02` — transport HTTP real opt-in + teste real atrás de flag.
3. `PEDROCORE-EVAL-HARNESS-02` — granularidade de risco e casos com memória habilitada.
4. `PEDROCORE-REPORT-MEMORY-02` — retenção/limpeza e consulta filtrada (`ReportMemoryQuery` completo em rota).

## 12. Recomendação de commit

Commit recomendado (não executado):

```text
feat: consolidar inteligencia de ecossistema do Veltrix
```
