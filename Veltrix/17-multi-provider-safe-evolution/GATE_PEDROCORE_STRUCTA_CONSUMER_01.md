# Gate Veltrix — Structa Consumer 01

Gate: `GATE-PEDROCORE-STRUCTA-CONSUMER-01`.

Data: 14/08/2026.

Veredito: **PASS**.

Esta microfrente não é a Etapa 13 do Structa e realizou zero inferências.

## Critérios

| Critério | Evidência | Resultado |
| --- | --- | --- |
| `Structa` resolve canonicamente | `Structa`/`structa` → `structa`; lookalike → `unknown` | PASS |
| caller legítimo | registry oficial, `registered`, `technical_tool` | PASS |
| mismatch/identidade inválida | missing, unknown, origem divergente e role comum negados | PASS |
| task restrita | somente `qa_report_analysis`; crítica diferente bloqueada antes do provider | PASS |
| Gemini autorizado localmente | matriz explícita para Structa não produtivo | PASS |
| default-off | `ChatRequest.allow_real_provider=false` | PASS |
| fallback real | kill switch permanece `false` | PASS |
| providers indevidos | OpenAI, Claude, DeepSeek e Grok denied | PASS |
| regressão FinGuard/Veltrix | regras anteriores preservadas | PASS |
| provider real/rede | guard estrutural; contadores `0/0` | PASS |
| `.obsidian` | cinco hashes idênticos; ignore por paths exatos; zero exclusão | PASS |
| porta 3333 | PID 14744/FinGuard identificado e preservado | PASS |
| Structa repo | HEAD/status preservados, sem escrita | PASS |
| testes | focados 66; integral 751 passed/7 skipped | PASS |
| documentação | 130 documentos, 726 links resolvidos, zero violações | PASS |
| segredos | nenhum valor exibido, persistido ou commitado | PASS |

## Limite operacional preservado

O código reconhece e autoriza o consumer; a credencial operacional não foi
provisionada de forma persistente. A futura Etapa 13 deverá iniciar uma
instância dedicada com `PEDROCORE_CALLER_REGISTRY` process-scoped e entregar a
mesma credencial ao client por configuração protegida. A ausência dessa
credencial continua fail-closed e não reduz o veredito deste Gate de
onboarding de código/policy.

## Evidência de autorização sem inferência

```text
project=structa
identity=registered
role=technical_tool
task=qa_report_analysis
provider=gemini
authorization=allowed
realFallbackEnabled=false
plannedRealCalls=0
actualRealCalls=0
```

Negativos comprovados:

```text
unknown consumer → denied
Structa + local_trusted → denied
Structa + common_consumer → denied
Structa + OpenAI/Claude/DeepSeek/Grok → denied
Structa + critical task fora da allowlist → blocked antes do provider
```

## Validações

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_project_context.py tests/test_caller_identity_authorization.py tests/test_real_provider_policy.py tests/test_structa_consumer_onboarding.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check --no-cache app/modules/project_context/service.py app/modules/provider_authorization/service.py tests/test_structa_consumer_onboarding.py
.\.venv\Scripts\python.exe -m app.modules.docs_graph.service
```

O build web também passou. O Ruff integral registrou somente o F401
preexistente em `tests/test_report_memory.py`, fora do escopo e do diff.

## Confirmações negativas

- nenhuma inferência Gemini ou de outro provider;
- nenhuma chamada externa ou teste de credencial;
- nenhum fallback real;
- nenhuma mudança em chave real ou `.env` real;
- nenhuma identidade falsa, wildcard ou permissão herdada;
- nenhuma alteração no Structa, FinGuard ou processo da porta 3333;
- nenhuma Etapa 13 ou Etapa 14;
- nenhum push, tag, PR ou merge.

## Próxima ação

Parar. Uma nova autorização explícita será necessária para retornar ao Structa
e executar exatamente uma inferência na Etapa 13.

## Links relacionados

- [[PEDROCORE_STRUCTA_CONSUMER_01]]
- [[ETAPA_2_IDENTIDADE_AUTORIZACAO]]
- [[../MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[../MOC_QA_RELEASE_GATE]]
- [[../MOC_VERSOES_STATUS]]
