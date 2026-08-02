# Report Intelligence Foundation

Frente: `PEDROCORE-MODEL-FOUNDATION-01`
Atualizado em: 08/07/2026

Links: [[INTELLIGENCE_LAYER_OVERVIEW]] | [[EVALUATION_FOUNDATION]] | [[../00_MAPEAMENTO_GERAL_PEDROCORE]]

## 1. O que é

Fundação para o PedroCore ingerir **relatórios técnicos do ecossistema** (QA, release, arquitetura) no futuro, extrair sinais determinísticos e montar memória técnica.

Princípio central e inegociável:

> **Relatórios técnicos NÃO treinam IA.** Eles alimentam sinais e memória técnica, que no futuro poderão virar contexto de prompt. Nunca são usados para treinamento, fine-tuning ou autoaprendizado.

## 2. O que existe nesta frente

- Módulo `apps/api/app/modules/report_intelligence/` (`schemas.py`, `service.py`).
- Schemas: `TechnicalReportInput`, `ReportSignal`, `ReportMemorySummary`.
- Serviço `ReportIntelligenceService` com três métodos determinísticos:
  - `normalize_report(report)` — trim, lowercase de status/ids, dedupe e limites de listas (sanitização obrigatória);
  - `extract_signals(report)` — sinais explicáveis por regex/status;
  - `summarize_memory(project_id, reports)` — agregação em memória volátil, **sem persistência**.

## 3. O que NÃO existe nesta frente

- Banco persistente novo.
- Embeddings / RAG real.
- Rota pública de ingestão (ver seção 7).
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

`normalize_report` é etapa obrigatória antes de qualquer extração: trim, normalização de status, deduplicação e teto de tamanho/quantidade. Conteúdo sensível segue a política `sanitize` da Intelligence Layer; relatórios nunca devem conter segredos, e sinais nunca reproduzem chaves.

## 7. Rotas futuras (documentadas, NÃO implementadas)

- `POST /api/reports/ingest` — ingestão de relatório técnico por payload (exigirá autenticação/policy, sem path, sem persistência até decisão própria).
- `GET /api/project-memory/{project_id}/summary` — leitura da memória técnica agregada.

Nenhuma rota nova foi criada nesta frente; o módulo é consumível internamente e por testes.

## 8. Testes

`apps/api/tests/test_report_intelligence.py` cobre: validação de campos obrigatórios, sinais por status, criticidade de provider real/banco real, smoke/full coverage, `QA_RISK_CRITICAL` sem invalidar suíte passed, normalização determinística e agregação de memória sem persistência.
