# MOC Testes

Mapa de comandos, testes padrao e testes opt-in.

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

Resultado atual (`PEDROCORE-QA-SAFETY-HARDENING-01`, commit `d6106b7`): `341 passed, 6 skipped, 2 warnings`.

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
