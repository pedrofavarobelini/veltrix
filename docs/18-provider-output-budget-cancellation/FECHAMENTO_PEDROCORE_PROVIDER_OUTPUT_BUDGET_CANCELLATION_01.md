# Fechamento — PEDROCORE-PROVIDER-OUTPUT-BUDGET-CANCELLATION-01

Detalhamento técnico em
[[PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]].

> **Evolução posterior.** A frente
> `FINGUARD-PEDROCORE-ASSISTANT-FINAL-CLOSE-01` auditou este trabalho e
> corrigiu dois defeitos residuais no commit `b0d637b`: o fechamento de
> transporte era registrado como concluído sem evidência, e os metadados de
> uso eram descartados no caminho de truncamento. Ver
> [[PEDROCORE_ASSISTANT_FINAL_CLOSURE_01]].
>
> Os campos `transport_cancel_requested` e `transport_cancelled_locally`
> citados abaixo foram substituídos por `transport_close_requested` e
> `transport_close_outcome`, que distinguem tentativa de confirmação.

---

## 1. Escopo executado

```text
orçamento explícito de saída               feito
política centralizada de orçamento         feito
teto global de segurança                   feito
limite por modelo                          feito
limite por task                            feito
timeout de transporte explícito            feito
cliente Gemini assíncrono nativo           feito
remoção de asyncio.to_thread do Gemini     feito
lifecycle explícito do cliente             feito
detecção de truncamento                    feito
coleta segura de metadados de tokens       feito
taxonomia coerente de término              feito
completion_ambiguous preservado            feito
ausência de retry automático               preservada
ausência de segundo provider após timeout  preservada
ausência de chamadas paralelas             preservada
observabilidade sem conteúdo sensível      feito
testes determinísticos sem rede            feito
documentação reconciliada                  feito
```

## 2. Arquivos

### Criados

```text
apps/api/app/modules/output_budget/__init__.py
apps/api/app/modules/output_budget/schemas.py
apps/api/app/modules/output_budget/service.py
apps/api/tests/gemini_fakes.py
apps/api/tests/test_provider_generation_characterization.py
apps/api/tests/test_output_budget.py
apps/api/tests/test_gemini_adapter_budget.py
apps/api/tests/test_provider_output_budget_pipeline.py
apps/api/tests/test_output_budget_observability.py
docs/18-provider-output-budget-cancellation/PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01.md
docs/18-provider-output-budget-cancellation/FECHAMENTO_PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01.md
```

### Alterados

```text
apps/api/app/modules/providers/base.py
apps/api/app/modules/providers/gemini_provider.py
apps/api/app/modules/provider_catalog/schemas.py
apps/api/app/modules/provider_catalog/service.py
apps/api/app/modules/orchestration/service.py
apps/api/app/modules/audit/schemas.py
apps/api/app/modules/contracts/codes.py
apps/api/app/modules/observability/schemas.py
apps/api/app/modules/observability/service.py
apps/api/app/modules/observability/gemini_smoke.py
apps/api/tests/conftest.py
apps/api/tests/test_caller_identity_authorization.py
apps/api/tests/test_provider_auto_characterization.py
apps/api/tests/test_provider_model_binding.py
apps/api/tests/test_provider_real_fallback_controlled.py
apps/api/tests/test_provider_routing_enforced.py
apps/api/tests/test_provider_health_circuit_breaker.py
apps/api/tests/test_real_provider_policy.py
apps/api/tests/test_shadow_routing.py
apps/api/tests/test_shared_credential_privilege.py
```

Os oito últimos arquivos de teste receberam **apenas** `**kwargs` na assinatura
dos dublês de adapter. Nenhuma asserção foi alterada, removida ou enfraquecida.

### Não alterados

```text
apps/api/pyproject.toml
apps/api/uv.lock
apps/api/.env / .env.example
qualquer arquivo do FinGuard
qualquer arquivo da SPA
```

## 3. Commits

```text
1  test: caracterizar budget e timeout do provider Gemini
2  feat: adicionar orcamento seguro de saida do provider
3  feat: migrar Gemini para cliente async com timeout de transporte
4  test: validar truncamento cancelamento e chamada unica
5  docs: fechar output budget e cancelamento do provider
```

## 4. Testes

```text
baseline anterior à frente     570 passed, 7 skipped
suíte completa após a frente   703 passed, 7 skipped
eval harness                   14/14, risk_level="none", exit 0
ruff (arquivos da frente)      aprovado
chamadas externas reais        zero
```

O guard global de provider real (`tests/conftest.py`) permaneceu ativo durante
toda a execução e nenhum teste o disparou.

## 5. Resultado

O risco confirmado no mapeamento foi corrigido no que é tecnicamente
corrigível:

| Risco original | Estado |
| --- | --- |
| Sem orçamento de saída | **corrigido** — teto global, por modelo e por task |
| Sem timeout de transporte | **corrigido** — `HttpOptions.timeout` derivado |
| Cliente síncrono em thread | **corrigido** — `client.aio`, sem `to_thread` |
| Cliente nunca fechado | **corrigido** — `aclose()` em `finally` |
| Truncamento invisível | **corrigido** — `finish_reason` lido e sinalizado |
| `finish_reason`/`usage_metadata` descartados | **corrigido** |
| `PROVIDER_COMPLETION_AMBIGUOUS` nunca emitido | **corrigido** |
| `provider_non_retryable` nunca produzido | **corrigido** |
| Geração órfã após timeout | **reduzido, não eliminado** — ver limitações |

## 6. Limitações

Declaradas explicitamente, sem atenuação:

1. **Fechar a conexão local não comprova interrupção da geração remota.** A
   migração para o cliente assíncrono entregou cancelamento da task, do await
   e do transporte local — não do lado do Google.
2. **`X-Server-Timeout` não é garantia de cancelamento remoto.** É uma
   sinalização enviada junto do request; o comportamento do servidor não foi
   verificado e não pode ser verificado sem chamada real.
3. **`completion_ambiguous` continua necessário** e continua sendo aplicado a
   todo timeout após dispatch.
4. **Nenhum timeout torna retry seguro automaticamente.** Retry permanece
   inexistente, e o fallback real permanece bloqueado após qualquer término
   não pre-dispatch.
5. **O cenário Organizar não foi revalidado nesta frente.** Continua pendente.
6. **Nenhuma chamada real foi feita.** Toda a validação é determinística.
7. **O orçamento reduz risco, mas não prova a causa do timeout histórico.** Não
   há evidência de que a ausência de orçamento tenha causado os timeouts de
   ~30 s e ~60 s observados no Organizar.
8. **Os valores de budget podem precisar de ajuste** após uma sonda real
   autorizada que meça `usage_metadata` em produção.
9. **Custo real não foi medido.** Nenhuma API paga adicional foi ativada.
10. **O circuit breaker não foi alterado** e continua abrindo imediatamente em
    conclusão ambígua, com a mesma limitação de escopo por processo.

## 7. Riscos residuais

| Risco | Estado |
| --- | --- |
| Geração órfã após timeout de transporte | **reduzido** — agora existe teto temporal e de tokens, mas o término remoto continua desconhecido |
| Esgotamento de pool de threads | **eliminado no caminho Gemini** — não há mais `to_thread` |
| Valores de budget mal dimensionados | **plausível** — derivados de `response_style`, não de medição |
| Timeouts inconsistentes entre caminhos | **corrigido** — o smoke passou a usar a mesma política, sem valor próprio |
| Lint pré-existente em `tests/test_report_memory.py` | **fora de escopo** — arquivo não tocado por esta frente |

## 8. Estado do sistema

```text
Assistente FinGuard              operacional
Gemini real                      comprovado anteriormente
cenários homologados             3/4
Organizar                        pendente por variabilidade/timeout
output budget                    corrigido localmente
timeout de transporte            implementado
cliente async                    implementado
cancelamento local/transporte    reforçado
cancelamento remoto              não comprovável
completion_ambiguous             preservado
providers reais ativos           somente Gemini
push                             não
tag                              não
```
