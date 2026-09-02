# Gate Veltrix — Elyra Onboarding V1 Textual

Gate: `GATE-PEDROCORE-ELYRA-ONBOARDING-V1-TEXTUAL`.

Data: 25/08/2026.

Veredito: **PASS**.

## Critérios executáveis

| Critério | Evidência | Resultado |
| --- | --- | --- |
| identidade Elyra | registry, `registered`, `project_id=elyra`, `common_consumer` | PASS |
| origin correto | `origin_system=elyra`; mismatch bloqueado | PASS |
| Project Context | contexto read-only e fronteiras não clínicas | PASS |
| capability mínima | somente `wellbeing_report_interpretation` | PASS |
| futuras capabilities | multimodal, learning e generic chat bloqueados | PASS |
| input schema | `elyra-textual-input/v1`, strict e versionado | PASS |
| output schema | `elyra-textual-output/v1`, validado antes de publicar | PASS |
| provider policy | mock offline ou auto/Gemini não produtivo sem fallback | PASS |
| provider/model mismatch | `ELYRA_PROVIDER_MISMATCH` | PASS |
| provider indisponível | erro explícito, zero fallback | PASS |
| timeout | bloqueio controlado, uma tentativa, zero retry | PASS |
| correlation | preservada em response/output/audit | PASS |
| idempotência | replay, conflito e duplicata concorrente provados | PASS |
| internal failure | `ELYRA_INTERNAL_FAILURE`, nunca success | PASS |
| caller desconhecido | missing/unknown deny antes do provider | PASS |
| regressão | 959 testes backend aprovados | PASS |
| rede/provider real | zero chamadas na suíte padrão | PASS |

## Comandos e resultados

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests/test_elyra_consumer_onboarding.py -q
# 44 passed, 1 skipped, 2 warnings

.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
# 959 passed, 21 skipped, 2 warnings

.\.venv\Scripts\python.exe -m ruff check --no-cache .
# All checks passed!

.\.venv\Scripts\python.exe -m app.modules.eval_harness.run
# 14/14, risk_level=none

.\.venv\Scripts\python.exe -m app.modules.docs_graph.service
# 155 documentos, 822 links resolvidos, zero violações
```

O build `npm.cmd run build` em `apps/web` passou; o metadata gerado foi
restaurado e não integra o diff.

Os dois warnings são preexistentes e não funcionais: depreciação da Config
class do Pydantic em `app/core/config.py` e aviso de compatibilidade
Starlette/httpx no TestClient. Pyright não é aplicável neste workspace.

## Smoke real

`test_real_elyra_gemini_once_without_fallback` existe e é isolado por
`PEDROCORE_RUN_REAL_ELYRA_TESTS=true`. A execução atual não recebeu autorização
para provider real; o teste permaneceu skipped e nenhum resultado real foi
simulado como evidência.

## Warnings e dívida técnica

- a idempotência é intencionalmente volátil/process-local; persistência
  distribuída exigiria contrato e infraestrutura futuros;
- a credencial operacional Elyra precisa ser provisionada fora do Git na
  instância que atender a Stage 09;
- multimodal Stage 12 e dataset/learning Stage 13 continuam bloqueados;
- não existe segundo provider/modelo homologado; Elyra real é Gemini-only;
- timeout mantém conclusão remota ambígua e nunca autoriza retry.

## Decisão

O onboarding de código, policy, schemas e QA está concluído. Parar no lado
Veltrix. A retomada da Stage 09 ocorre em execução separada no repositório
Elyra, consumindo exatamente [[../10-contratos/CONTRATO_ELYRA_TEXTUAL_V1]].

## Links

- [[PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]]
- [[../10-contratos/CONTRATO_ELYRA_TEXTUAL_V1]]
- [[../MOC_TESTES]]
- [[../MOC_QA_RELEASE_GATE]]
- [[../MOC_VERSOES_STATUS]]
