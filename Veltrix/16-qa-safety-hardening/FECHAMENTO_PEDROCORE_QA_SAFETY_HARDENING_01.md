# Fechamento — PEDROCORE-QA-SAFETY-HARDENING-01

Data: 2026-07-09
Base: `main` @ `7656ff4` (working tree limpo antes da frente; tag v7.0.0 em `33b2c04`).

## Resumo da frente

Endurecimento de QA e segurança do Veltrix sem alteração funcional:
guard estrutural de provider real nos testes, suítes novas de safety
(provider real, report memory, policy negativa, contrato do `/api/orchestrate`),
extensão determinística do eval harness (11 → 14 casos) e documentação de
QA/release gate. O Veltrix já estava finalizado; esta frente reduz risco de
regressão e fortalece o release gate.

## Arquivos alterados

| Arquivo | Mudança |
|---|---|
| `apps/api/app/modules/eval_harness/fixtures.py` | +3 casos determinísticos (única mudança em `app/`; só dados de fixture, sem lógica) |

## Arquivos criados — testes

| Arquivo | Conteúdo |
|---|---|
| `apps/api/tests/conftest.py` | Guard autouse: bloqueia e detecta invocação de provider real; respeita `PEDROCORE_RUN_REAL_PROVIDER_TESTS`; marker `expected_guarded_call` |
| `apps/api/tests/test_provider_real_safety.py` | 12 testes: defaults, bloqueio dos 5 providers reais, provider inválido, bypass aninhado, mock/local_qa sem chave, guard, eval sem provider real |
| `apps/api/tests/test_report_memory_safety.py` | 9 testes: defaults do schema, flag inválida = off, snapshot null, não-injeção no prompt (spy), isolamento entre projetos, 422 controlado |
| `apps/api/tests/test_policy_negative_cases.py` | 10 testes: policy bloqueia antes de qualquer provider (spy no registry), payload perigoso/inválido, disclaimer inquebrável, sem stack trace |
| `apps/api/tests/test_orchestrate_contract_safety.py` | 8 testes: shape de sucesso/bloqueio/422/401, contrato de audit e release gate, ausência de campos sensíveis |
| `apps/api/tests/test_eval_harness_extended.py` | 6 testes: registro dos casos novos, providers seguros, determinismo entre runs, harness sem provider real |

## Arquivos criados — docs (`docs/16-qa-safety-hardening/`)

`QA_SAFETY_HARDENING_PLAN.md`, `MATRIZ_TASK_PROVIDER_POLICY.md`,
`RELEASE_GATE_CHECKLIST.md`, `REPORT_MEMORY_SAFETY.md`,
`PROVIDER_REAL_SAFETY.md`, este fechamento.

## Comandos executados (validação final)

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
$env:ALLOW_REAL_PROVIDER="false"; $env:ALLOW_LOCAL_MODEL="false"
$env:CONTEXT_FROM_MEMORY="false"; $env:REPORT_MEMORY_ENABLED="false"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m app.modules.eval_harness.run
```

## Resultados

- Baseline pré-frente: **296 passed, 6 skipped** · eval **11/11**.
- Final: **341 passed, 6 skipped, 2 warnings** (exit 0) — +45 testes, mesmos
  6 skips opt-in preservados, mesmos 2 warnings pré-existentes (deprecations).
- Eval harness: **14/14 passed, failed 0, risk_level "none"** (exit 0).

## Confirmação de escopo

- Provider real não chamado: guard do `conftest.py` prova por construção;
  suíte verde = zero invocações não autorizadas.
- Rede real não chamada: providers reais interceptados antes do SDK;
  `local_model` sem transport; Playwright/OCR/multimodal seguem default-off.
- Report Memory continua default-off, opt-in, e **não é treinamento**
  (`REPORT_MEMORY_SAFETY.md`).
- local_model real continua fora do escopo (nenhum backend instalado,
  nenhum transport implementado).
- FinGuard intocado; `apps/api/.env` intocado; `qa:finalize:02` intocado.
- Nenhum commit/push/tag/merge realizado nesta frente.

## Riscos restantes

- O guard cobre `generate_response`; um provider novo adicionado ao registry
  precisa ser incluído em `REAL_PROVIDER_CLASSES` do `conftest.py` (o teste
  `test_real_providers_report_real_provider_true_in_registry` ajuda a lembrar).
- O guard atua só em pytest; execução manual da API com chave real em `.env` e
  `allow_real_provider=true` continua possível por design (opt-in humano).
- Warnings de deprecation (Pydantic v2 class-based config, starlette
  testclient) seguem pré-existentes; tratáveis em frente futura.

## Próximos passos opcionais (futuro, fora desta frente)

- `regression_report.py`: comparador de baseline do eval harness
  (decidido não implementar; `run.py` já dá exit code + JSON).
- Migrar `Settings` para `ConfigDict` (remove warning Pydantic).
- Incluir novos providers reais no guard automaticamente via
  `provider_registry.list_providers()` quando houver mais de 5.

## Links relacionados

- [[../MOC_QA_SAFETY_HARDENING]]
- [[QA_SAFETY_HARDENING_PLAN]]
- [[RELEASE_GATE_CHECKLIST]]
- [[../MOC_VERSOES_STATUS]]
- [[../08_CHANGELOG]]
