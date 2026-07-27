# MOC Testes

Mapa de comandos, testes padrao e testes opt-in.

## Resultado atual — 2026-07-27

- Fechamento: [[18-provider-output-budget-cancellation/FECHAMENTO_PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]].
- Backend integral: `703 passed, 7 skipped, 2 warnings`.
- Eval harness: `14/14 passed`, `risk_level="none"`.
- Ruff aprovado nos arquivos da frente; zero chamadas externas reais.
- Novos arquivos: `test_provider_generation_characterization.py`,
  `test_output_budget.py`, `test_gemini_adapter_budget.py`,
  `test_provider_output_budget_pipeline.py`,
  `test_output_budget_observability.py` e o helper `gemini_fakes.py`.
- O fake substitui apenas o *cliente* do SDK: `GenerateContentConfig` e
  `HttpOptions` continuam sendo os tipos reais do `google-genai` instalado.
- Pendência conhecida e fora do escopo desta frente: `ruff` acusa um import não
  usado em `tests/test_report_memory.py`, arquivo não tocado aqui.

## Resultado anterior — 2026-07-26

- Fechamento: [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]].
- Backend integral: `570 passed, 7 skipped, 2 warnings`.
- Eval harness: `14/14 passed`, `risk_level="none"`.
- Ruff aprovado; zero chamadas externas reais.

## Comandos seguros

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - secao 21.
- [[10-api/EXEMPLOS_API_MVP]]
- [[MOC_QA_SAFETY_HARDENING]] - suite safety hardening e checklist atual.
- [[16-qa-safety-hardening/RELEASE_GATE_CHECKLIST]]
- [[04-comandos/COMANDOS_POWERSHELL_V1]]
- [[04-comandos/V5_1_9_COMANDOS]]

## Suite backend padrao

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -q
```

Resultados históricos permanecem no [[08_CHANGELOG]]. O checkpoint integral atual das Etapas 1–7 é `570 passed, 7 skipped, 2 warnings`.

Teste direcionado da frente `FINGUARD-PEDROCORE-ASSISTANT-REAL-PROVIDER-QA-01`:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_real_provider_policy.py tests/test_providers.py tests/test_real_optin.py tests/test_safe_mode.py tests/test_orchestrate_api.py
```

Resultado local: `28 passed, 7 skipped, 2 warnings`. Gemini real nao roda nesse comando.

Suite integral atual:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Resultado mais recente: `570 passed, 7 skipped, 2 warnings`.

Eval harness deterministico (sem provider real, sem rede):

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
uv run python -m app.modules.eval_harness.run
```

Resultado atual: `14/14 passed`, `risk_level="none"`.

Auditoria local documentada:

- [[15-estudo-pedrocore/PEDROCORE_AUDITORIA_STUDY_MAP_01]] - resultado de pytest, eval harness e rotas locais.
- [[15-estudo-pedrocore/PEDROCORE_VEREDITO_FINAL]] - veredito de readiness e riscos restantes.
- [[16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]] - fechamento safety hardening.

## Testes opt-in

- `apps/api/tests/test_real_optin.py`
- Flags `PEDROCORE_RUN_REAL_*_TESTS=true`.
- Gemini real usa `PEDROCORE_RUN_REAL_GEMINI_TESTS=true`.
- Nao fazem parte do teste padrao.
- Podem exigir chave real, dependencia local ou efeito externo; precisam de aprovacao humana.

## Testes por area

- Root/health: `test_root.py`, `test_health.py`.
- Providers/chat/safe mode: `test_providers.py`, `test_chat.py`, `test_safe_mode.py`.
- Orquestracao/API: `test_orchestration_flow.py`, `test_orchestrate_api.py`.
- QA/release: `test_qa_analysis.py`, `test_qa_response.py`, `test_qa_flow.py`, `test_release_gate.py`, `test_release_hardening.py`.
- FinGuard: `test_finguard_contract.py`, `test_finguard_enforcement.py`.
- Reader/OCR/visual/Playwright/exploration: `test_artifact_reader.py`, `test_ocr_guard.py`, `test_visual_qa.py`, `test_multimodal_guard.py`, `test_playwright_guard.py`, `test_exploration.py`.
- Fundacao de inteligencia: `test_intelligence_layer.py`, `test_report_intelligence.py`, `test_local_model_contract.py`, `test_evaluation_foundation.py`.
- Ecossistema/memoria/local model/eval: `test_ecosystem_contract.py`, `test_report_memory.py`, `test_local_model_provider.py`, `test_eval_harness.py`.
- Safety hardening: `test_provider_real_safety.py`, `test_report_memory_safety.py`, `test_policy_negative_cases.py`, `test_orchestrate_contract_safety.py`, `test_eval_harness_extended.py`.
- Observabilidade/Gemini opt-in: `test_observability.py`, `test_gemini_smoke.py`.
- Multi-provider seguro: `test_provider_catalog.py`, `test_caller_identity_authorization.py`, `test_shared_credential_privilege.py`, `test_provider_model_binding.py`, `test_shadow_routing.py`, `test_provider_routing_enforced.py`, `test_provider_health_circuit_breaker.py`, `test_provider_real_fallback_controlled.py`.
