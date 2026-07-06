# MOC Testes

Mapa de comandos, testes padrao e testes opt-in.

## Comandos seguros

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - secao 21.
- [[10-api/EXEMPLOS_API_MVP]]
- [[04-comandos/COMANDOS_POWERSHELL_V1]]
- [[04-comandos/V5_1_9_COMANDOS]]

## Suite backend padrao

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -q
```

Resultado final registrado no fechamento: `216 passed, 6 skipped, 2 warnings`.

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
