# PEDROCORE-PROVIDER-OUTPUT-BUDGET-CANCELLATION-01

Orçamento de saída, timeout de transporte, cliente assíncrono e certeza de
término no adapter Gemini.

Relacionados: [[ETAPA_6_HEALTH_STATE_CIRCUIT_BREAKER]],
[[ETAPA_7_FALLBACK_REAL_CONTROLADO]], [[FECHAMENTO_ETAPAS_1_A_7]],
[[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]].

---

## 1. Problema

O adapter Gemini executava a geração sem nenhum limite sob controle do
PedroCore:

```text
cliente síncrono dentro de asyncio.to_thread
+ sem GenerateContentConfig
+ sem max_output_tokens
+ sem HttpOptions.timeout
+ sem leitura de finish_reason
+ sem leitura de usage_metadata
+ cliente criado por requisição e nunca fechado
```

Consequências confirmadas em código antes da correção:

1. o teto de saída era inteiramente o default do modelo, desconhecido pelo
   PedroCore;
2. o transporte HTTP não tinha teto temporal algum;
3. `asyncio.wait_for` encerrava apenas a espera local — a thread continuava;
4. uma resposta truncada era publicada como sucesso silencioso;
5. custo e consumo de tokens eram invisíveis.

## 2. Evidências

| Evidência | Origem |
| --- | --- |
| Adapter sem configuração de geração | `providers/gemini_provider.py` (versão anterior) |
| Transporte sem timeout | `google/genai/_api_client.py`: `if 'timeout' not in args: args['timeout'] = None` |
| SDK não repete por padrão | `_api_client.py`: `retry_args(None)` → `stop_after_attempt(1)` |
| Timeout não interrompe a thread | `tests/test_provider_health_circuit_breaker.py::test_wait_for_timeout_does_not_stop_to_thread_work` |
| Timeout não inicia secundário | `tests/test_provider_real_fallback_controlled.py::test_ambiguous_timeout_never_starts_secondary_while_work_can_remain_alive` |

## 3. SDK e versão

```text
pacote:    google-genai
declarado: >=0.8.0        (apps/api/pyproject.toml)
resolvido: 2.9.0          (apps/api/uv.lock)
instalado: 2.9.0          (google/genai/version.py)
```

Capacidades confirmadas no pacote instalado e agora efetivamente usadas:

| Capacidade | Símbolo real |
| --- | --- |
| Orçamento de saída | `types.GenerateContentConfig.max_output_tokens` |
| Timeout de transporte | `types.HttpOptions.timeout` (**milissegundos**) |
| Cliente assíncrono | `Client.aio` → `AsyncClient.models.generate_content` |
| Fechamento explícito | `AsyncClient.aclose()` |
| Truncamento | `types.FinishReason.MAX_TOKENS` |
| Uso de tokens | `GenerateContentResponseUsageMetadata` |

A dependência **não foi alterada**: nenhum `uv add`, nenhuma mudança em
`pyproject.toml` ou `uv.lock`.

## 4. Arquitetura anterior

```text
orquestração
 └─ asyncio.wait_for(timeout = PEDROCORE_PROVIDER_TIMEOUT_SECONDS)
     └─ GeminiProvider.generate_response
         └─ asyncio.to_thread(run_request)
             └─ genai.Client(api_key=...)               ← sem http_options
                 .models.generate_content(model, contents)  ← sem config
                     ← response.text                     ← descarta o resto
```

## 5. Arquitetura atual

```text
orquestração
 ├─ generation_plan_for(provider, model, task_type)
 │   ├─ output_budget_service.resolve(task_type, model_cap)
 │   └─ output_budget_service.transport_timeout_ms(orchestration_timeout)
 └─ asyncio.wait_for(timeout = orchestration_timeout)
     └─ GeminiProvider.generate_response(..., output_budget, transport_timeout_ms)
         ├─ genai.Client(http_options=HttpOptions(timeout=<ms>))
         ├─ await client.aio.models.generate_content(
         │      config=GenerateContentConfig(max_output_tokens=<budget>))
         ├─ normalização: finish_reason + usage_metadata
         └─ finally: await client.aio.aclose()
```

## 6. Orçamento de saída

Política central e pura em `app/modules/output_budget/`:

```text
effective_output_budget = min(global_cap, model_cap, task_cap)
```

| Camada | Onde vive | Valor atual |
| --- | --- | --- |
| Teto global de segurança | `output_budget/service.py` | `8192` |
| Teto por modelo | `ModelDefinition.max_output_tokens` (catálogo) | `gemini-3.5-flash` → `8192` |
| Teto por task | `_TASK_OUTPUT_CAPS` | ver abaixo |

Faixas por natureza de resposta:

| Faixa | Valor | Tasks |
| --- | --- | --- |
| Assistente / financeiro | `4096` | `assistant_chat`, `ecosystem_assistant`, `finance_advice`, `technical_explanation`, `code_help` |
| Estruturado | `3072` | QA, relatório, exploração, planejamento, `general_chat` |
| Conservador | `2048` | task desconhecida ou não catalogada |

### Justificativa dos valores

Os tetos derivam do `response_style` de cada task no `task_router`, **não de
medição de tokens**: até esta frente o `usage_metadata` era descartado e o
repositório nunca teve contagem real. São generosos o bastante para não
truncar resposta legítima e finitos o bastante para que nenhuma geração fique
sem teto.

O `4096` cobre as tasks conversacionais e financeiras — onde vivem os cenários
homologados do FinGuard (Dívidas, Economizar, Crescer) e o pendente
(Organizar) — com folga de várias vezes o tamanho observado nas respostas
homologadas. O `2048` é o piso para o que o sistema não caracterizou.

**Estes números podem precisar de ajuste após uma sonda real autorizada que
meça `usage_metadata` em produção.** Nada nesta frente mediu tokens reais.

### Invariantes

- `ChatRequest` continua **sem** qualquer campo de tokens, budget ou timeout;
- a política **não lê** payload, `metadata` nem `context`;
- valores inválidos (não inteiros, zero, negativos, `bool`) são descartados,
  nunca propagados;
- o adapter **recusa executar** sem orçamento válido resolvido pelo PedroCore.

## 7. Timeout de transporte

Regra única em `output_budget_service.transport_timeout_ms`:

```text
com_margem  = max(orquestracao - 2.0 s, 1.0 s)
transporte  = min(com_margem, orquestracao * 0.9)
resultado   = max(1, int(transporte * 1000))    ← milissegundos
```

Garantia testada em todo o intervalo aceito pelo clamp `[0.05 s, 120 s]`:

```text
transport_timeout < orchestration_wait_timeout
```

| Espera da orquestração | Timeout de transporte | Margem |
| --- | --- | --- |
| 0.05 s | 45 ms | ~5 ms |
| 30 s (default) | 27 000 ms | 3 s |
| 60 s | 54 000 ms | 6 s |
| 120 s | 108 000 ms | 12 s |

A margem existe para propagar a exceção, fechar o cliente, auditar e aplicar o
fallback seguro **antes** de a espera externa expirar.

Unidades são explicitamente distintas e a conversão acontece num único ponto:

```text
PEDROCORE_PROVIDER_TIMEOUT_SECONDS → segundos
HttpOptions.timeout                → milissegundos
```

Efeito colateral relevante: com `HttpOptions.timeout` definido, o SDK também
emite o header `X-Server-Timeout`. **Isso é uma sinalização, não uma garantia
de cancelamento remoto** — ver a seção 10.

## 8. Cliente assíncrono e lifecycle

O adapter usa `client.aio.models.generate_content` e **não usa mais**
`asyncio.to_thread`. O cliente é fechado em `finally`, o que cobre:

```text
sucesso
erro do provider
timeout de transporte
cancelamento da task
erro de normalização (truncamento e finish_reason anormal)
```

Falha no fechamento nunca mascara o resultado nem a exceção originais.

O lifecycle é **por operação**. Não há cliente global compartilhado nesta
frente: não existe hoje um ciclo de vida de aplicação que garantisse
fechamento correto, e o ganho não justificaria o estado global.

Retry permanece desligado: o PedroCore **nunca** passa `HttpRetryOptions`, e o
default do SDK instalado é `stop_after_attempt(1)`.

## 9. Truncamento e finish_reason

`finish_reason` passou a ser lido e classificado:

| `finish_reason` | Tratamento |
| --- | --- |
| `STOP` | conclusão normal |
| `FINISH_REASON_UNSPECIFIED` | conclusão normal |
| ausente, com texto utilizável | aceito; registrado como `None` |
| ausente, sem texto utilizável | erro de execução preexistente |
| `MAX_TOKENS` | **truncamento** → `PROVIDER_OUTPUT_TRUNCATED` |
| `SAFETY`, `RECITATION`, `BLOCKLIST`, `PROHIBITED_CONTENT`, `SPII`, `MALFORMED_FUNCTION_CALL`, `LANGUAGE`, `UNEXPECTED_TOOL_CALL`, `OTHER`, demais | conservador → `PROVIDER_OUTPUT_REJECTED` |

Política de truncamento:

```text
MAX_TOKENS
→ resposta considerada incompleta
→ texto parcial NÃO é publicado
→ sem chamada de continuação
→ sem retry
→ sem segundo provider
→ encerramento seguro existente (Mock)
→ warning e código internos registrados
```

Truncamento **nunca é inferido do tamanho do texto**: só evidência explícita
do provider decide. As mensagens técnicas carregam apenas o rótulo do
`finish_reason`, nunca o conteúdo gerado.

## 10. Taxonomia e certeza de término

Nenhum enum novo foi criado. Foram aproveitados os estados existentes,
incluindo `provider_non_retryable`, que estava declarado e nunca era produzido:

| Evento | `FailureClassification` | `CompletionCertainty` | `external_dispatch` |
| --- | --- | --- | --- |
| Sucesso | `success` | `completed` | `true` |
| Espera da orquestração expirou | `completion_ambiguous` | `ambiguous` | `true` |
| Transporte HTTP expirou | `completion_ambiguous` | `ambiguous` | `true` |
| Truncamento / finish anormal | `provider_non_retryable` | `completed` | `true` |
| Configuração ausente | `provider_pre_dispatch` | `not_dispatched` | `false` |
| Circuito aberto | `provider_pre_dispatch` | `not_dispatched` | `false` |

### O limite honesto do cancelamento

Quatro coisas diferentes, deliberadamente não confundidas:

```text
1. cancelamento da task          → real e comprovado
2. cancelamento local do await   → real e comprovado
3. fechamento da conexão HTTP    → real e comprovado
4. cancelamento da geração remota → NÃO COMPROVADO
```

Migrar para o cliente assíncrono entregou (1), (2) e (3). **Não entregou (4).**
Fechar a conexão local não prova que o modelo parou de gerar do outro lado.

Por isso:

- os fatos de transporte são registrados como
  `transport_close_requested` e `transport_close_outcome`
  (`not_attempted` · `confirmed` · `failed` · `unknown`), que distinguem
  tentativa de confirmação — ver [[PEDROCORE_ASSISTANT_FINAL_CLOSURE_01]];
- a certeza de conclusão **permanece** `ambiguous`, mesmo com o fechamento
  local confirmado;
- nenhum estado chamado `cancelamento_real` foi criado;
- `X-Server-Timeout` **não** é descrito como garantia de cancelamento remoto.

Consequências preservadas, sem exceção:

```text
completion_ambiguous
→ sem retry
→ sem segundo provider
→ sem fallback real
→ sem chamada paralela
→ circuit breaker mantém o tratamento conservador
→ Mock seguro conforme a política existente
```

## 11. Códigos de contrato

Novos, aditivos:

| Código | Severidade | Quando |
| --- | --- | --- |
| `PROVIDER_OUTPUT_TRUNCATED` | warning | `finish_reason=MAX_TOKENS` |
| `PROVIDER_OUTPUT_REJECTED` | warning | `finish_reason` anormal |
| `PROVIDER_TRANSPORT_TIMEOUT` | warning | transporte HTTP expirou |

Lacuna corrigida: `PROVIDER_COMPLETION_AMBIGUOUS` existia desde a Etapa 6 e
**nunca era emitido**. Agora acompanha todo timeout após dispatch.

Compatibilidade preservada: o `error_code` público de qualquer timeout continua
sendo `PROVIDER_TIMEOUT`. Os estados novos entram como warnings adicionais, que
já são aditivos por contrato.

## 12. Observabilidade

Campos novos na auditoria e na projeção local — todos numéricos ou rótulos:

```text
output_budget_effective     output_budget_source      output_budget_clamped
output_budget_global_cap    output_budget_model_cap   output_budget_task_cap
orchestration_timeout_ms    transport_timeout_ms
transport_close_requested   transport_close_outcome
provider_finish_reason      provider_output_truncated
provider_input_tokens       provider_output_tokens    provider_total_tokens
```

Métricas de token vêm **exclusivamente** de `usage_metadata` real. Ausência
nunca vira estimativa, nunca vira falha. Um `total_token_count` menor que
`input + output` é descartado como incoerente; maior é preservado, porque
modelos com raciocínio contabilizam `thoughts_token_count`.

Nada de sensível foi adicionado e a retenção **não foi ampliada**: o
comportamento de `public_response` permanece exatamente o anterior. Sanitizer e
redaction seguem intactos, com testes que provam ausência de prompt, contexto
financeiro e credencial nos novos metadados.

O campo `retry` continua constante `{"attempted": false, "count": 0}` — agora
com comentário explicando que isso é **por construção**, não por omissão: não
existe retry no adapter, na orquestração nem no SDK.

## 13. Testes

Arquivos novos, todos sem rede e sem credencial real:

| Arquivo | Cobertura |
| --- | --- |
| `tests/gemini_fakes.py` | fake do cliente; os tipos são os REAIS do SDK |
| `tests/test_provider_generation_characterization.py` | invariantes válidas antes e depois |
| `tests/test_output_budget.py` | composição, precedência, valores inválidos, unidades |
| `tests/test_gemini_adapter_budget.py` | config, `HttpOptions`, async, lifecycle, `finish_reason`, tokens |
| `tests/test_provider_output_budget_pipeline.py` | truncamento, timeout, chamada única, contratos |
| `tests/test_output_budget_observability.py` | metadados novos e ausência de conteúdo sensível |

O guard global de `tests/conftest.py` continua ativo. Os dublês de adapter dos
testes preexistentes receberam `**kwargs` — mudança de assinatura de test
double, sem alteração de nenhuma asserção.

## 14. Compatibilidade

Preservado e testado:

```text
POST /api/orchestrate          contrato retrocompatível
provider=auto                  inalterado
model ausente no consumidor    inalterado
FinGuard                       não tocado; não controla budget nem timeout
SPA                            inalterada
Mock seguro                    inalterado
local_qa                       inalterado; sem orçamento
release gate                   inalterado; só local_qa aprova
safe mode                      inalterado
circuit breaker                default-off, comportamento conservador mantido
fallback real                  default-off, ainda bloqueado após timeout
uma IA por requisição          preservado
Gemini                         único provider real ativo
```

Somente o `GeminiProvider` declara `supports_generation_budget`. Todos os
demais adapters seguem exatamente o caminho anterior.
