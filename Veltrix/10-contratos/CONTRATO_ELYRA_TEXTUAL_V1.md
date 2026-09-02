# Contrato Elyra Textual V1

Contrato: `elyra-textual/v1`.

Status: **IMPLEMENTADO** em 25/08/2026.

Este contrato é a fronteira oficial e mínima entre Elyra e Veltrix para a
Stage 09. Ele reutiliza `POST /api/orchestrate`, Caller Identity, Project
Context, Task Router, provider/model binding, audit e erros já nativos.

## Identidade e capability

| Campo | Valor obrigatório |
| --- | --- |
| `project_id` autenticado | `elyra` |
| `origin_system` declarado | `elyra` |
| `identity_strength` | `registered` |
| `caller_role` | `common_consumer` |
| `allowed_origins` | contém `elyra` |
| `task_type` | `wellbeing_report_interpretation` |
| operação | `interpret_deterministic_report` |

A credencial vem de `PEDROCORE_CALLER_REGISTRY` e é enviada no header
`X-Veltrix-Api-Key`. O payload não escolhe identidade. Missing, unknown,
credencial compartilhada, `local_trusted`, outro projeto, outro papel ou
origem divergente são negados.

Na instância dedicada que atende Elyra, use o registry por caller e mantenha a
chave global legada `PEDROCORE_INTERNAL_API_KEY` vazia. Configurar as duas
simultaneamente faria o gate legado exigir a chave global antes de resolver o
registry; essa combinação não é o deployment suportado para a Stage 09.

Exemplo de entrada do registry, sempre provisionada fora do Git:

```json
{
  "credential_id": "elyra-textual-v1",
  "api_key": "<segredo somente no ambiente/runtime>",
  "project_id": "elyra",
  "role": "common_consumer",
  "environment": "development",
  "allowed_origins": ["elyra"]
}
```

## Request HTTP

Campos do envelope Elyra:

```json
{
  "message": "interpretar_relatorio_deterministico",
  "mode": "tecnico",
  "provider": "mock",
  "model": null,
  "task_type": "wellbeing_report_interpretation",
  "origin_system": "elyra",
  "allow_real_provider": false,
  "allow_mock_fallback": true,
  "correlation_id": "elyra-stage09-request-001",
  "idempotency_key": "elyra-stage09-idempotency-001",
  "context": {
    "contractVersion": "elyra-textual/v1",
    "inputSchemaVersion": "elyra-textual-input/v1",
    "operation": "interpret_deterministic_report",
    "aiInferenceConsent": true,
    "report": {}
  }
}
```

`context.report` não é `{}` em uma chamada real: deve ser o snapshot
determinístico completo produzido pela Elyra com estes discriminadores:

| Campo | Valor/schema |
| --- | --- |
| `schemaVersion` | `report_snapshot/v1` |
| `analyticsVersion` | `elyra-analytics/v1` |
| `cycleHeuristicVersion` | `elyra-cycle/v1` |
| `timeZone` | timezone IANA válida |
| `window` / `previousWindow` | janelas ordenadas de 28, 56 ou 90 dias |
| `series` | um ponto único e ordenado para cada dia da janela |
| `metrics` | `mood`, `anxiety`, `energy`, `sleepDurationMinutes` |
| `cycle` | dados somente quando o opt-in de ciclo estiver ligado |
| `associations.prePeriodEnergy` | associação temporal, nunca causalidade |
| `dataQuality` | contagens limitadas à janela |

Os schemas Pydantic usam `extra="forbid"`. Diário integral, mídia, artefatos,
metadata livre, memória, `system_prompt` externo e modelo local não pertencem a
esta capability. `aiInferenceConsent` é independente e precisa ser `true`.

## Provider policy

Dois modos são válidos:

| Uso | `provider` | `allow_real_provider` | `allow_mock_fallback` |
| --- | --- | --- | --- |
| CI/QA determinística | `mock` | `false` | sem efeito operacional |
| execução real controlada | `auto` | `true` | `false` |

O consumer comum nunca envia `provider=gemini` nem `model`. O Veltrix pode
selecionar apenas `gemini + gemini-3.5-flash`, somente para identidade Elyra
registrada e ambiente não produtivo. Produção, providers diferentes, modelo
escolhido pelo caller, fallback Mock e fallback real secundário são negados.
Provider/modelo respondente diferente do binding produz
`ELYRA_PROVIDER_MISMATCH`.

## Response

O envelope comum acrescenta campos opcionais, sem quebrar consumers legados:

- `correlation_id`;
- `idempotency_replayed`;
- `elyra`, presente apenas após validação integral do output.

`elyra` segue `elyra-textual-output/v1`:

```json
{
  "contractVersion": "elyra-textual/v1",
  "outputSchemaVersion": "elyra-textual-output/v1",
  "operation": "interpret_deterministic_report",
  "correlationId": "elyra-stage09-request-001",
  "sourceReportSchemaVersion": "report_snapshot/v1",
  "sourceAnalyticsVersion": "elyra-analytics/v1",
  "language": "pt-BR",
  "summary": "texto não clínico validado",
  "observations": [
    {
      "category": "data_quality",
      "evidencePath": "dataQuality",
      "text": "descrição vinculada ao snapshot"
    }
  ],
  "limitations": [
    "Ausência de dado não equivale a zero e limita qualquer interpretação.",
    "Tendências e associações não estabelecem diagnóstico nem causalidade."
  ],
  "disclaimer": "Conteúdo informativo e não clínico. Não constitui diagnóstico, prescrição ou afirmação causal e deve ser interpretado pela pessoa usuária.",
  "safety": {
    "diagnosticClaim": false,
    "prescription": false,
    "causalClaim": false,
    "facialEmotionAsFact": false,
    "fictitiousEmotionPercentage": false
  }
}
```

JSON inválido, campo extra, versão divergente, correlação divergente, output
parcial ou safety incompatível são recusados. O texto bruto não é publicado
como sucesso.

## Correlation e idempotência

`correlation_id` e `idempotency_key` são obrigatórios para esta task e aceitam
3–128 caracteres alfanuméricos mais `.`, `_`, `:`, `-`.

- mesma key + mesmo request: devolve cópia do primeiro outcome, com
  `idempotency_replayed=true` e o mesmo `audit_id`;
- mesma key + request diferente: `ELYRA_IDEMPOTENCY_CONFLICT`, sem dispatch;
- duplicatas concorrentes compartilham uma única execução;
- cache volátil e limitado a 256 outcomes;
- chave bruta nunca entra em audit: somente fingerprint SHA-256 truncado;
- não há retry depois de dispatch externo.

## Error contract

| Situação | Código |
| --- | --- |
| credencial ausente/desconhecida | `CALLER_CREDENTIAL_MISSING` / `CALLER_CREDENTIAL_UNKNOWN` |
| origem divergente | `CALLER_ORIGIN_MISMATCH` |
| identidade/papel Elyra não registrado | `ELYRA_CALLER_NOT_REGISTERED` |
| task/capability não autorizada | `PROJECT_POLICY_BLOCKED` |
| schema/correlation/idempotency inválido | `ELYRA_INPUT_SCHEMA_INVALID` |
| consentimento de inferência ausente | `ELYRA_CONSENT_REQUIRED` |
| modo de provider/fallback proibido | `ELYRA_PROVIDER_POLICY_DENIED` |
| provider/modelo respondente divergente | `ELYRA_PROVIDER_MISMATCH` |
| provider elegível indisponível | `PROVIDER_REAL_UNAVAILABLE` |
| timeout | `PROVIDER_TIMEOUT` |
| output inválido | `ELYRA_OUTPUT_INVALID` |
| key reaproveitada com payload diferente | `ELYRA_IDEMPOTENCY_CONFLICT` |
| exceção interna | `ELYRA_INTERNAL_FAILURE` |

Todos os casos retornam `status=blocked`, `elyra=null` e nunca convertem erro
em sucesso. Timeout não destrava retry nem fallback.

## Fronteiras

- Veltrix não acessa PostgreSQL, Supabase, Storage ou filesystem da Elyra.
- Somente o snapshot explicitamente preparado cruza a fronteira.
- A task descreve métricas já calculadas; não recalcula score oficial.
- Não diagnostica, prescreve, afirma condição clínica ou causalidade.
- Não trata expressão facial como emoção objetiva nem inventa percentuais.
- Multimodal Stage 12 e dataset/learning Stage 13 permanecem desabilitados e
  sem payload antecipado.

## Links

- [[../17-multi-provider-safe-evolution/PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]]
- [[../17-multi-provider-safe-evolution/GATE_PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]]
- [[CONTRATO_ORQUESTRACAO]]
- [[../MOC_INTEGRACOES]]
- [[../MOC_SEGURANCA]]
