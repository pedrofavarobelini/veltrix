# QA Safety Hardening — Plano da Frente

Frente: **PEDROCORE-QA-SAFETY-HARDENING-01**
Base: `main` @ `7656ff4` (pós v7.0.0). PedroCore já estava finalizado localmente
como core seguro/orquestrador central; esta frente é melhoria de QA, não conserto.

## Objetivo

Endurecer QA, segurança de providers, Report Memory, policy enforcement,
contratos do `/api/orchestrate` e eval harness, reduzindo risco de regressão e
fortalecendo o release gate — sem alterar comportamento funcional.

## Escopo

1. Guard estrutural de provider real nos testes (`tests/conftest.py`).
2. Testes de Provider Real Safety (`tests/test_provider_real_safety.py`).
3. Testes de Report Memory Safety (`tests/test_report_memory_safety.py`).
4. Testes negativos de policy (`tests/test_policy_negative_cases.py`).
5. Contract tests do `/api/orchestrate` (`tests/test_orchestrate_contract_safety.py`).
6. Extensão determinística do eval harness (3 casos novos em
   `app/modules/eval_harness/fixtures.py` + `tests/test_eval_harness_extended.py`).
7. Documentação desta pasta (`docs/16-qa-safety-hardening/`).

## Fora de escopo

- local_model real (instalação de backend, transport de rede, download de modelo);
- RAG real, fine-tuning, autoaprendizado;
- chamada a provider real (Gemini/OpenAI/Claude/DeepSeek/Grok) ou rede real;
- FinGuard (repositório e integração);
- alteração de `apps/api/.env` ou exposição de chaves;
- mudança em `qa:finalize:02`;
- snapshot automático ou dependência nova de teste;
- `regression_report.py` (registrado como futuro opcional);
- commit/push/tag/merge.

## Riscos

- O guard autouse do `conftest.py` interage com toda a suíte: mitigado
  respeitando `PEDROCORE_RUN_REAL_PROVIDER_TESTS` e validando que os 6 skips
  opt-in permanecem.
- Casos novos de eval poderiam ser flakey: mitigado usando apenas mock/local_qa
  e assertions sobre saídas determinísticas.
- Testes de memória poderiam vazar estado in-process: mitigado com
  `report_memory_service.reset()` em fixture autouse.

## Critérios de aceite

1. Pytest 100% verde com os 6 skips opt-in preservados.
2. Eval harness 14/14 passed, `risk_level: none`.
3. Nenhum provider real invocado (guard prova por construção).
4. Defaults imutáveis: `allow_real_provider=false`, `allow_local_model=false`,
   `context_from_memory=false`, `PEDROCORE_REPORT_MEMORY_PERSISTENCE=off`.
5. Nenhuma alteração funcional em `apps/api/app` além das fixtures do harness.
6. FinGuard e `qa:finalize:02` intocados.

## Ordem de execução

1. Auditoria e baseline (296 passed / 6 skipped; eval 11/11).
2. `conftest.py` + revalidação da suíte inteira.
3. Testes P1→P4 (provider real, report memory, policy, contrato).
4. Fixtures novas do eval harness + testes estendidos.
5. Documentação.
6. Validação final (pytest + eval harness + `git status`).

## Links relacionados

- [[../MOC_QA_SAFETY_HARDENING]]
- [[MATRIZ_TASK_PROVIDER_POLICY]]
- [[RELEASE_GATE_CHECKLIST]]
- [[FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]]
- [[../MOC_TESTES]]
