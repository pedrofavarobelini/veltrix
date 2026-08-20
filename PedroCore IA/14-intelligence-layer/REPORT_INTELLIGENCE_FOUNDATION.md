# Report Intelligence Foundation

Frente: `PEDROCORE-REPORT-INTELLIGENCE-V2` — IMPLEMENTED
Atualizado em: 20/08/2026

Links: [[INTELLIGENCE_LAYER_OVERVIEW]] | [[EVALUATION_FOUNDATION]] | [[../00_MAPEAMENTO_GERAL_PEDROCORE]]

## 1. O que é

Fundação para o PedroCore ingerir **relatórios técnicos do ecossistema** (QA, release, arquitetura) no futuro, extrair sinais determinísticos e montar memória técnica.

Princípio central e inegociável:

> **Relatórios técnicos NÃO treinam IA.** Eles alimentam sinais e memória técnica, que no futuro poderão virar contexto de prompt. Nunca são usados para treinamento, fine-tuning ou autoaprendizado.

## 2. O que existe nesta frente

- Módulo `apps/api/app/modules/report_intelligence/` (`schemas.py`, `service.py`).
- `IntelligenceReportEnvelopeV2`: Common Envelope `schema_version=2.0`,
  `report_id`, tipo, producer autenticado, projeto e correlation IDs.
- Payloads tipados iniciais: `interaction_quality`, `qa_evidence`,
  `risk_analysis` e `execution_outcome`. Os dois últimos são somente contratos;
  o Risk Engine ainda não existe nesta etapa.
- `TechnicalReportInput` permanece LEGACY e é convertido por adapter para V2
  antes da lógica de ingestão.
- Serviço `ReportIntelligenceService` com três métodos determinísticos:
  - `normalize_report(report)` — trim, lowercase de status/ids, dedupe e limites de listas (sanitização obrigatória);
  - `extract_signals(report)` — sinais explicáveis por regex/status;
  - `summarize_memory(project_id, reports)` — agregação em memória volátil, **sem persistência**.

## 3. O que NÃO existe nesta frente

- PostgreSQL ou banco persistente novo.
- Embeddings / RAG real.
- Leitura de repositórios externos ou do FinGuard real.
- Persistência em arquivo.
- Interpretação de relatório como treinamento.

## 4. Signal types e severidades

Signal types: `qa_passed`, `qa_failed`, `provider_real_blocked`, `provider_real_used`, `database_safety_ok`, `database_safety_risk`, `smoke_coverage`, `full_coverage`, `documentation_gap`, `architecture_risk`, `release_gate_blocked`, `release_gate_passed`, `next_step`, `human_review_required`.

Severidades: `info`, `low`, `medium`, `high`, `critical`.

Regras principais de extração:

| Evidência | Sinal | Severidade |
|---|---|---|
| status `passed`/`pass`/`success` | `qa_passed` | `info` (`low` se houver findings) |
| status `failed`/`fail`/`error` | `qa_failed` | `high` |
| provider real usado | `provider_real_used` | `critical` |
| provider real bloqueado | `provider_real_blocked` | `info` (comportamento esperado) |
| banco real usado | `database_safety_risk` | `critical` |
| banco real não usado | `database_safety_ok` | `info` (negação tem precedência) |
| menção a `smoke` | `smoke_coverage` | `medium` |
| menção a `full` | `full_coverage` | `info` |
| `review_required` / `can_advance=false` | `human_review_required` | `medium` (`high` se failed) |
| `QA_RISK_CRITICAL` | `architecture_risk` | `critical` — **não invalida** suíte reportada como `passed` |
| `next_steps` do relatório | `next_step` | `info` |

## 5. Conservadorismo obrigatório

O serviço **extrai sinais, não decide sozinho por produção**:

- todo sinal carrega `evidence` e `confidence` explicáveis;
- sinais `critical`/`high` sempre exigem revisão humana (ver [[EVALUATION_FOUNDATION]]);
- `ReportMemorySummary` é recomendação agregada, nunca aprovação automática.

## 6. Sanitização

`normalize_envelope` é a representação interna canônica. O adapter V1 preserva
`metadata`, `findings`, `suggested_fixes`, `signals/evidence` disponíveis e
correlation IDs. Conteúdo sensível é redigido antes da persistência local.

## 7. Rotas

- LEGACY: `POST /api/reports/analyze` e `/api/reports/ingest` recebem V1,
  autorizam o caller e adaptam para V2 internamente.
- V2: `POST /api/reports/v2/analyze` e `/api/reports/v2/ingest` recebem o
  envelope estrito. Versão desconhecida é rejeitada, sem interpretação silenciosa.
- `GET /api/project-memory/{project_id}/summary` mantém leitura isolada.

`producer` precisa coincidir com o `credential_id` autenticado. Duplicata de
`report_id` no mesmo projeto não cria novo efeito e retorna
`REPORT_DUPLICATE_IGNORED`.

## 8. Testes

`test_report_intelligence_v2.py` cobre adapter V1, quatro tipos V2,
preservação, versão, provenance, isolamento, LEGACY e idempotência. A suíte V1
continua em `test_report_intelligence.py` e `test_report_memory.py`.
