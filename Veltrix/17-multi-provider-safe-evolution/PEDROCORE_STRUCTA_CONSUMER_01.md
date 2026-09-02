# Veltrix — onboarding seguro do consumer Structa

Frente: `PEDROCORE-STRUCTA-CONSUMER-01`.

Status: **implementado e validado offline** em 14/08/2026.

## Objetivo

Registrar `origin_system=Structa` como consumer externo de menor privilégio,
sem contornar a identidade por credencial e sem realizar inferência real.

O fluxo autorizado passa a ser:

```text
origin_system=Structa
→ project_id=structa
→ credencial registrada em PEDROCORE_CALLER_REGISTRY
→ identity_strength=registered
→ caller_role=technical_tool
→ task_type=qa_report_analysis
→ provider=gemini
→ allow_real_provider=true explícito
→ autorização local allowed
→ execução real somente em Gate separado
```

`origin_system` continua sendo alegação validada. Sem credencial registrada, o
Structa permanece negado; a identidade `local_trusted` não recebeu permissão
para representar consumers externos.

## Project Context

| Campo | Valor |
| --- | --- |
| `project_id` | `structa` |
| `display_name` | `Structa` |
| origem normalizada | `Structa` e `structa` → `structa` |
| task permitida | somente `qa_report_analysis` |
| read-only | `true` |
| executa comandos | `false` |
| escreve arquivos | `false` |

Matching continua exato: `StructaXYZ` resolve para `unknown`.

## Caller Identity

O mecanismo oficial foi reutilizado sem criar autenticação paralela:
`PEDROCORE_CALLER_REGISTRY`, enviado ao endpoint por
`X-Veltrix-Api-Key`.

Entrada operacional esperada, sempre provisionada fora do Git:

```json
{
  "credential_id": "structa-report-intelligence",
  "api_key": "<segredo somente no ambiente/runtime>",
  "project_id": "structa",
  "role": "technical_tool",
  "environment": "development",
  "allowed_origins": ["structa"]
}
```

O `.env` real não foi alterado nesta frente. Um registry persistente contendo
somente Structa mudaria o comportamento dos callers locais existentes. A
futura instância dedicada da Etapa 13 deve receber uma credencial registrada
process-scoped, com o mesmo segredo entregue ao client sem impressão ou
persistência em Git.

## Provider Authorization

Nova regra explícita, sem wildcard:

| Identidade | Projeto | Papel | Ambiente | Provider |
| --- | --- | --- | --- | --- |
| `registered` | `structa` | `technical_tool` | dev/local/test/qa/staging | `gemini` |

Não foram autorizados produção, `common_consumer`, `local_trusted`, OpenAI,
Claude, DeepSeek, Grok ou providers futuros. As regras FinGuard e Veltrix
permaneceram independentes e inalteradas.

A matriz de provider não possui eixo `task_type`. A restrição de task existe
no Project Context e é aplicada pelo policy enforcement antes do provider em
fluxos críticos. Para Structa, `qa_failure_diagnosis` foi provada como
bloqueada antes de qualquer adapter.

## Defaults e fallback

- `allow_real_provider=false` continua sendo o default do request.
- `PEDROCORE_REAL_FALLBACK_ENABLED=false` continua sendo o default.
- O onboarding não adicionou fallback real nem provider secundário.
- A futura Etapa 13 deve reprovar se o provider real falhar ou usar fallback.

## Threat model

| Ameaça | Controle observado |
| --- | --- |
| alegar Structa sem credencial | `CALLER_CREDENTIAL_MISSING`/`UNKNOWN` |
| usar credencial de outro projeto | `CALLER_ORIGIN_MISMATCH` |
| papel inadequado | matriz default-deny |
| origem parecida/fuzzy | resolução exata; `StructaXYZ=unknown` |
| provider diferente | matriz nega todos exceto Gemini |
| task crítica fora da allowlist | policy bloqueia antes do provider |
| `allow_real_provider=true` isolado | insuficiente sem identidade e matriz |
| segredo em Git/docs | apenas placeholder e presença booleana |

## Regularização local do Obsidian

Cinco arquivos preexistentes sob `Veltrix/.obsidian/` foram classificados
como configuração local de aplicação, aparência, plugins, grafo e workspace.
Nenhum era rastreado. A política Git passou a ignorar somente os cinco paths
exatos; a pasta inteira não foi ocultada.

| Arquivo | Bytes | SHA-256 antes/depois |
| --- | ---: | --- |
| `app.json` | 2 | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` |
| `appearance.json` | 2 | `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` |
| `core-plugins.json` | 696 | `763cf20a921fd9955735b278006820b90b207b2fc04d9e79ca648279c7c14276` |
| `graph.json` | 514 | `eeec9f4167244e57e57eb26d92a35a9efe99c00a4a12e7d86325343c50464890` |
| `workspace.json` | 5127 | `9983b2c51913a90aa938198d9937252c77a434c3176f38b97458a8561bada510` |

Tamanho, timestamp e hash permaneceram idênticos. Nenhum arquivo foi apagado,
movido, sobrescrito ou commitado.

## Porta 3333

A porta 3333 continuou ocupada pelo processo Node PID 14744, pertencente ao
backend FinGuard preexistente. Ele foi identificado em modo read-only e não
foi encerrado.

O Veltrix já aceita `uvicorn ... --port <porta-livre>`. A futura Etapa 13
deve descobrir uma porta livre no pre-gate e passá-la como argumento, sem
fixar 3334 nem alterar a arquitetura.

## QA offline

- Baseline focada anterior: `51 passed, 2 warnings`.
- Suite focada após onboarding: `66 passed, 2 warnings`.
- Suite backend integral: `751 passed, 7 skipped, 2 warnings`.
- Ruff dos arquivos alterados: PASS.
- Build web: PASS; o metadata gerado foi restaurado e não entrou no diff.
- Grafo documental: 130 documentos, 726 links resolvidos, zero violações.
- Guard autouse de testes: nenhum adapter real executado.
- Full Ruff mantém um F401 preexistente e fora do diff em
  `tests/test_report_memory.py`; não foi mascarado nem corrigido nesta frente.

## Evidência local

```text
originDeclared=Structa
contextProjectId=structa
identityProjectId=structa
identityStrength=registered
callerRole=technical_tool
provider=gemini
configured=true
homologation=homologated_real
allowRealProvider=true
authorizationResult=allowed
realFallbackEnabled=false
openaiAuthorizationResult=denied
unknownAuthorizationResult=denied
plannedRealCalls=0
actualRealCalls=0
```

O avaliador terminou antes de qualquer adapter. Nenhuma chave, header ou
credencial real foi registrada na evidência.

## Commits técnicos

- `b2d7203` — `feat: registrar consumer Structa com menor privilegio`.
- `2f57d4a` — `test: validar fronteiras do consumer Structa`.
- `9b209d9` — `chore: regularizar estado local do Obsidian`.

## Links relacionados

- [[GATE_PEDROCORE_STRUCTA_CONSUMER_01]]
- [[ETAPA_2_IDENTIDADE_AUTORIZACAO]]
- [[FIX_CREDENCIAL_COMPARTILHADA]]
- [[../MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[../MOC_INTEGRACOES]]
- [[../MOC_SEGURANCA]]
- [[../MOC_TESTES]]
