# PedroCore — Elyra Onboarding V1 Textual

Frente: `PEDROCORE-ELYRA-ONBOARDING-V1-TEXTUAL`.

Data: 25/08/2026.

Status: **IMPLEMENTADO E VALIDADO OFFLINE**.

## Objetivo e veredito

O PedroCore passou a reconhecer Elyra legitimamente no pipeline nativo. Não
foi criada arquitetura paralela, identidade falsa nem permissão herdada de
PedroCore, FinGuard ou Structa.

```text
PEDROCORE_ELYRA_ONBOARDING = PASS
```

## Fluxo nativo

```text
X-PedroCore-Api-Key
→ PEDROCORE_CALLER_REGISTRY
→ project_id=elyra / registered / common_consumer
→ origin_system=elyra validado
→ Project Context allowlist
→ task_type=wellbeing_report_interpretation
→ schema elyra-textual-input/v1
→ provider/model binding
→ mock determinístico OU auto/Gemini sem fallback
→ schema elyra-textual-output/v1
→ audit + correlation + idempotência
```

O mapeamento estrutural com Graphify confirmou esses pontos de inserção no
fluxo existente router → identity → project/task/policy → binding/auth →
provider → audit → response. Um diretório de saída criado pela ferramenta foi
identificado como untracked e removido integralmente antes da implementação;
nenhum artefato Graphify permaneceu no repositório.

## Project Context e capability

- `project_id=elyra`, matching exato;
- plataforma de acompanhamento emocional, autoconhecimento, hábitos,
  relatórios e acompanhamento profissional autorizado;
- read-only, sem comandos, filesystem ou escrita;
- uma única capability: `wellbeing_report_interpretation`;
- multimodal e learning continuam não registrados/negados;
- nenhum acesso direto ao banco ou Storage Elyra.

## Caller e provider

- identidade somente por credencial registrada;
- papel mínimo `common_consumer`;
- origem permitida somente `elyra`;
- Gemini somente em ambiente não produtivo;
- caller pede `provider=auto` e nunca escolhe provider/modelo real;
- CI usa `provider=mock` determinístico;
- execução real exige `allow_real_provider=true` e
  `allow_mock_fallback=false`;
- produção, provider divergente, fallback e identidade ambígua são default-deny.

## Schemas e segurança

O módulo `app/modules/elyra_textual/` contém schemas strict, validação de
entrada/saída, mock determinístico e cache idempotente volátil. O input usa o
snapshot `report_snapshot/v1`/`elyra-analytics/v1`/`elyra-cycle/v1`; o output é
`elyra-textual-output/v1` e só é publicado após validação completa.

As safety declarations obrigam `false` para diagnóstico, prescrição,
causalidade, emoção facial como fato e percentual fictício. Diário integral,
mídia, artifacts, memória, system prompt livre e local model são rejeitados.

Contrato executável: [[../10-contratos/CONTRATO_ELYRA_TEXTUAL_V1]].

## Correlation, idempotência e audit

- correlation ID preservado em response, output e audit;
- key de idempotência nunca é armazenada em claro;
- replay igual devolve o mesmo outcome/audit sem duplicar execução;
- payload divergente com a mesma key é bloqueado;
- duplicatas concorrentes compartilham uma execução;
- cache em memória limitado a 256 itens;
- timeout e dispatch externo nunca iniciam retry Elyra.

## QA executada

| Validação | Resultado |
| --- | --- |
| suíte Elyra focada | `44 passed, 1 skipped` |
| regressão dirigida de callers/providers | correção aditiva validada; incluída na suíte integral |
| backend integral | `959 passed, 21 skipped, 2 warnings` |
| Ruff integral | PASS |
| eval harness | `14/14`, `risk_level=none` |
| Pyright | não aplicável: sem binário/configuração no workspace |
| providers externos na suíte | zero; guard estrutural ativo |
| smoke real Elyra | não executado; opt-in exclusivo permaneceu desligado |
| build web | PASS; metadata gerado restaurado sem diff |
| grafo documental | 155 documentos, 822 links, zero violações |

O teste real opcional usa `PEDROCORE_RUN_REAL_ELYRA_TESTS=true` e
`PEDROCORE_ELYRA_QA_CREDENTIAL`. Quando autorizado e corretamente
provisionado, faz uma única chamada `provider=auto`, exige Gemini/modelo
respondente, timeout configurado, correlation preservado e fallback false.

## Compatibilidade

- consumers legados mantêm defaults e payloads existentes;
- `correlation_id`, `idempotency_key` e `elyra` são aditivos/opcionais fora da
  task Elyra;
- respostas 401 legadas não ganham `correlation_id=null`; o campo só aparece
  quando fornecido;
- regras FinGuard, Structa e PedroCore permaneceram independentes;
- nenhum default global de routing foi alterado.

## Escopo negativo confirmado

- nenhuma alteração no repositório Elyra;
- nenhuma chamada Gemini real, rede externa ou uso de segredo;
- nenhuma implementação multimodal, dataset ou learning;
- nenhuma conexão direta a dados Elyra;
- nenhum push, tag, deploy, merge, rebase ou reset destrutivo;
- nenhum ADR necessário: a mudança é aditiva e reutiliza arquitetura aprovada.

## Links

- [[GATE_PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]]
- [[../10-contratos/CONTRATO_ELYRA_TEXTUAL_V1]]
- [[ETAPA_2_IDENTIDADE_AUTORIZACAO]]
- [[ETAPA_3_PROVIDER_MODEL_BINDING]]
- [[../MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[../MOC_INTEGRACOES]]
- [[../MOC_TESTES]]
