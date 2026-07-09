# Fechamento — PEDROCORE-MODEL-FOUNDATION-01

Atualizado em: 08/07/2026

Links: [[../14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]] | [[../00_MAPEAMENTO_GERAL_PEDROCORE]] | [[FECHAMENTO_PEDROCORE_FINAL]]

## 1. Objetivo da frente

Preparar o PedroCore IA **arquiteturalmente** para evoluir de orquestrador multi-provider para núcleo de inteligência própria do ecossistema, com fundação segura para Intelligence Layer, Report Intelligence, memória técnica futura, avaliação de respostas, contrato de Local Model Provider e documentação honesta dos limites.

Entrega correta desta frente: *"PedroCore preparado arquiteturalmente para evoluir para um núcleo de inteligência própria"* — **não** *"PedroCore agora é um modelo de IA próprio"*.

## 2. Estado inicial verificado

- Branch: `main`; HEAD: `d23d18d` (docs: sanear documentacao PedroCore IA v7).
- Tag `v7.0.0` → `33b2c04`; `v6.0.0` → `ee2ac68`.
- Working tree limpo.
- Baseline de testes: `216 passed, 6 skipped, 2 warnings`.
- `apps/api/.env` não tracked (apenas `.env.example`), não lido, não alterado.

## 3. O que foi implementado em código

1. **Intelligence Layer** (`apps/api/app/modules/intelligence_layer/`): `IntelligenceContextPolicy` (rejeita `allow_real_provider=true` por validação), `IntelligencePlan`, `IntelligenceLayerService.build_plan()` determinístico. Integrada ao `OrchestrationService` como metadado interno (`OrchestrationOutcome.intelligence_plan`), sem alterar `ChatResponse`/`OrchestrateResponse`.
2. **Report Intelligence Foundation** (`apps/api/app/modules/report_intelligence/`): `TechnicalReportInput`, `ReportSignal`, `ReportMemorySummary`; `normalize_report`/`extract_signals`/`summarize_memory` determinísticos, sem persistência, sem rede, sem RAG.
3. **Local Model Provider Contract** (`apps/api/app/modules/providers/local_model_contract.py`): contrato futuro do provider generativo local (`generation_supported=false` imposto por validação); não registrado no `provider_registry`.
4. **Evaluation Foundation** (`apps/api/app/modules/evaluation/`): checks determinísticos de segurança/coerência para planos e sinais.
5. **Task types novos** (`report_ingestion`, `project_memory_summary`, `model_foundation_review`, `intelligence_planning`), criticidade `medium`, permitidos apenas para `origin_system=pedrocore`. FinGuard não recebeu tasks novas.

## 4. O que foi apenas documentado (sem código)

- Rotas futuras `POST /api/reports/ingest` e `GET /api/project-memory/{project_id}/summary` — nenhuma rota nova foi criada.
- Conexão do `IntelligencePlan` ao Prompt Builder e exposição opcional em `OrchestrateResponse` — próxima frente.
- Implementação real do provider local (`PEDROCORE-LOCAL-MODEL-01`).
- Persistência de memória técnica (`PEDROCORE-REPORT-MEMORY-01`).
- Benchmark de avaliação (`PEDROCORE-EVAL-HARNESS-01`).

## 5. Testes

Novos arquivos:

- `tests/test_intelligence_layer.py`
- `tests/test_report_intelligence.py`
- `tests/test_local_model_contract.py`
- `tests/test_evaluation_foundation.py`

Nenhum teste existente foi apagado ou alterado. Resultado final: **`257 passed, 6 skipped, 2 warnings`** (216 anteriores + 41 novos; skips são os opt-in reais pré-existentes; warnings são deprecations Starlette/Pydantic pré-existentes).

## 6. Compatibilidade confirmada

- `GET /`, `GET /health`, `POST /api/chat`, `GET /api/providers`, `POST /api/orchestrate` inalterados.
- `ChatRequest`, `ChatResponse`, `OrchestrateResponse` sem mudança de contrato (teste dedicado confirma que `intelligence_plan` não vaza para a resposta pública).
- `allow_real_provider=false`, safe mode, mock fallback, `local_qa`, release gate, policy enforcement, Artifact Reader opt-in, real_features e contrato FinGuard read-only preservados.

## 7. Segurança confirmada

- Nenhum provider real chamado; `allow_real_provider=true` não usado em lugar nenhum.
- `apps/api/.env` não lido, não alterado, não stageado, não exposto.
- FinGuard não lido nem alterado; nenhuma task nova habilitada para FinGuard.
- Sem treinamento, sem fine-tuning, sem autoaprendizado, sem autoalteração de prompt, sem download de modelo, sem instalação de backend local, sem banco persistente novo, sem embeddings/RAG.
- Sem commit, push, tag ou merge nesta frente.

## 8. Limites atuais (honestos)

- Sem treinamento; sem fine-tuning; sem autoaprendizado; sem autoalteração de prompt.
- Sem substituição de APIs externas; sem provider real; sem provider local funcional.
- Sem banco persistente novo; sem RAG real; memória técnica é volátil.
- Sem leitura do FinGuard. O FinGuard já possui estrutura de assistente/tela/botão no repositório próprio, mas a integração do Assistente FinGuard via PedroCore ainda não foi implementada nesta frente. Essa integração pertence à frente `FINGUARD-PEDROCORE-ASSISTANT-01`.
- `IntelligencePlan` ainda não influencia o prompt nem a resposta — é fundação.

## 9. Roadmap recomendado

1. `PEDROCORE-MODEL-FOUNDATION-01` — **esta frente (concluída)**.
2. `PEDROCORE-ECOSYSTEM-FINALIZE-01` — consolidação do PedroCore como serviço do ecossistema.
3. `FINGUARD-PEDROCORE-ASSISTANT-01` — integração do Assistente FinGuard via PedroCore. O FinGuard já possui estrutura de assistente/tela/botão no repositório próprio; esta frente conecta essa estrutura ao PedroCore (frente própria, lado cliente fora deste repositório).
4. `PEDROCORE-REPORT-MEMORY-01` — persistência controlada da memória técnica.
5. `PEDROCORE-LOCAL-MODEL-01` — provider generativo local opt-in.
6. `PEDROCORE-EVAL-HARNESS-01` — harness de avaliação/benchmark.

## 10. Recomendação de commit

Commit recomendado (não executado):

```text
feat: preparar fundacao de inteligencia propria do PedroCore
```
