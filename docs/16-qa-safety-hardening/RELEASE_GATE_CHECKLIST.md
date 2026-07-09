# Release Gate — Checklist de QA/Safety

Checklist local do PedroCore IA após PEDROCORE-QA-SAFETY-HARDENING-01.
Não substitui `qa:finalize:02` (intocado por esta frente).

## Comandos

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

$env:ALLOW_REAL_PROVIDER="false"
$env:ALLOW_LOCAL_MODEL="false"
$env:CONTEXT_FROM_MEMORY="false"
$env:REPORT_MEMORY_ENABLED="false"

.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m app.modules.eval_harness.run
```

Observação de ambiente: use o Python do venv (`.venv\Scripts\python.exe`);
o `python` global pode não existir no PATH (alias da Microsoft Store).

## Critérios de aprovação

- [ ] Pytest 100% verde (referência: 341 passed) com exatamente 6 skipped
      (testes reais opt-in de `test_real_optin.py`).
- [ ] Eval harness com `failed: 0` e `risk_level: "none"` (referência: 14 casos).
- [ ] Exit code 0 nos dois comandos.
- [ ] `git status --short` sem alteração em `apps/api/.env`.

## Critérios de reprovação (qualquer um bloqueia)

- Qualquer teste falhando, inclusive erro de teardown com mensagem
  `REAL_PROVIDER_CALL_BLOCKED_BY_TEST_GUARD` (significa que algum caminho
  tentou executar provider real).
- Eval harness com `failed > 0` ou `risk_level != "none"`.
- Skips diferentes de 6 sem flag opt-in ativa (skip a mais = teste morto;
  skip a menos = teste real rodando sem autorização).
- Mudança nos defaults de `ChatRequest` (`allow_real_provider`,
  `allow_local_model`, `context_from_memory` devem ser `False`).

## Como confirmar que provider real não foi chamado

1. O guard de `tests/conftest.py` substitui `generate_response` dos 5 providers
   reais e **falha o teste** se qualquer um for invocado — suíte verde já é a
   prova estrutural.
2. `test_eval_harness_extended.py::test_harness_never_calls_real_provider`
   afirma lista de invocações vazia após rodar o harness completo.
3. Nenhuma variável `PEDROCORE_RUN_REAL_*_TESTS` pode estar `true` na execução
   padrão (senão o guard se desativa por design, para os testes reais opt-in).

## Como confirmar que o Report Memory continua seguro

1. `test_report_memory.py::test_persistence_off_by_default_and_ingest_stores_nothing`
   — ingest default retorna `status="disabled"`, `stored=false`.
2. `test_report_memory_safety.py::test_invalid_persistence_flag_value_behaves_as_off`
   — valor inválido na flag não liga a persistência.
3. `test_report_memory_safety.py::test_memory_not_injected_into_prompt_without_flag`
   — sem `context_from_memory=true`, o prompt não recebe `[Memória técnica]`.
4. `test_report_memory_safety.py::test_memory_does_not_leak_between_projects_via_orchestrate`
   — memória de um projeto não aparece para outro.
5. Smoke manual opcional: `POST /api/reports/ingest` sem flags deve responder
   `{"status": "disabled", "stored": false, ...}`.
