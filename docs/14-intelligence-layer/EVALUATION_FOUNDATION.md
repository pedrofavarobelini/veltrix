# Evaluation Foundation

Frente: `PEDROCORE-MODEL-FOUNDATION-01`
Atualizado em: 08/07/2026

Links: [[INTELLIGENCE_LAYER_OVERVIEW]] | [[REPORT_INTELLIGENCE_FOUNDATION]] | [[../00_MAPEAMENTO_GERAL_PEDROCORE]]

## 1. Por que existe

**Melhoria sem avaliação é perigosa.** Qualquer evolução do PedroCore rumo a inteligência própria (memória técnica, provider local, prompts melhores) precisa de uma forma de medir se um plano/resposta é seguro, coerente e compatível com as políticas — antes de confiar nele.

## 2. O que é nesta frente

Módulo `apps/api/app/modules/evaluation/` (`schemas.py`, `service.py`) com avaliação **determinística**:

- `EvaluationService.evaluate_intelligence_plan(plan)` — valida um `IntelligencePlan`;
- `EvaluationService.evaluate_report_signals(signals)` — valida sinais de relatório.

Schemas: `EvaluationCheck` (`name`, `passed`, `severity`, `message`) e `EvaluationResult` (`passed`, `checks`, `requires_human_review`, `risk_level`).

## 3. O que NÃO é

- Não é benchmark de LLM (fica para `PEDROCORE-EVAL-HARNESS-01`).
- Não compara com provider real.
- Não chama IA externa.
- Não aprova nada sozinha: sinais críticos sempre exigem revisão humana.

## 4. Checks mínimos

| Check | O que garante |
|---|---|
| `provider_real_not_allowed_by_default` | plano nunca habilita provider real |
| `no_auto_training_claim` | nenhuma alegação de autoaprendizado/treinamento automático |
| `no_finetuning_claim` | nenhuma alegação de fine-tuning |
| `no_sensitive_env_exposure` | nenhuma referência a `.env`/segredos/chaves |
| `requires_human_review_for_critical` | fluxo `release_gate_strict` exige revisão humana |
| `report_memory_is_not_training` | memory hints não tratam relatórios como treinamento |

Para sinais de relatório: `critical_signals_require_human_review` e `no_unauthorized_real_provider_usage`.

## 5. Semântica do resultado

- `passed=false` sempre que qualquer check falha.
- `requires_human_review=true` quando há falha, sinal `critical`/`high` ou o próprio plano exige revisão.
- `risk_level` deriva da pior severidade envolvida (`none` → `critical`).

## 6. Testes

`apps/api/tests/test_evaluation_foundation.py` cobre: plano limpo passa; plano com autoaprendizado/fine-tuning/referência a `.env` falha; release gate exige revisão humana; sinais críticos exigem revisão humana; `provider_real_used` reprova avaliação; sinais info passam sem revisão.
