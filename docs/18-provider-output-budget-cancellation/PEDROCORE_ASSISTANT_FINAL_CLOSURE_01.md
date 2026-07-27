# PEDROCORE — Fechamento final do Assistente IA

Frente: `FINGUARD-PEDROCORE-ASSISTANT-FINAL-CLOSE-01`.

Encerra, do lado do PedroCore, o Assistente IA do Ambiente Pessoal do FinGuard.

Relacionados:
[[PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]],
[[FECHAMENTO_PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]],
[[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]].

---

## 1. Veredito

```text
ASSISTENTE IA ENCERRADO COM LIMITAÇÃO EXTERNA DOCUMENTADA — HOMOLOGAÇÃO REAL 3/4
```

## 2. Auditoria residual e correções

A auditoria do intervalo `d973456..c459e80` confirmou **dois** defeitos residuais,
ambos corrigidos no commit `b0d637b`.

### 2.1 Fechamento de transporte registrado sem evidência

A auditoria derivava `transport_cancelled_locally=true` de uma flag de
capacidade da **classe** do adapter (`supports_transport_cancellation`), não do
fechamento real. Como `_aclose()` engolia a exceção, um `aclose()` que falhava
era registrado como fechamento concluído — falso positivo. E no timeout da
orquestração o resultado sequer é observável: a exceção que chega ao pipeline
vem do `asyncio.wait_for`, não do adapter.

Correção: `_aclose()` devolve o resultado observado e o adapter o anexa à
exceção. Os campos passaram a distinguir tentativa de confirmação:

| Campo | Semântica |
| --- | --- |
| `transport_close_requested` | o fechamento foi solicitado |
| `transport_close_outcome` | `not_attempted` · `confirmed` · `failed` · `unknown` |

`unknown` é o valor honesto quando o fechamento foi pedido mas não observado.

Invariante preservada: mesmo com `outcome="confirmed"`, o
`completion_certainty` de um timeout permanece `ambiguous`. Fechar a conexão
local continua não provando que a geração remota parou.

### 2.2 Metadados descartados no truncamento

`_normalize` extraía `usage_metadata` e então levantava
`ProviderOutputRejectedError` sem carregá-lo, perdendo tokens, orçamento e
timeout **justamente onde o custo já foi incorrido**.

Correção: a exceção preserva `input_tokens`, `output_tokens`, `total_tokens`,
`output_budget` e `transport_timeout_ms` até `provider_attempts`, auditoria e
observabilidade. Ausência de `usage_metadata` continua produzindo `None`.

### 2.3 Itens auditados sem defeito

| Item | Resultado |
| --- | --- |
| Taxonomia de timeout e truncamento | correta e preservada |
| Lifecycle do cliente | correto; agora com resultado observado |
| Contrato público da SPA | intacto — só `answer`, `suggestions`, `disclaimer` |
| Valores de budget | documentados como conservadores iniciais |
| Alterações de teste da frente anterior | só assinatura (`**kwargs`); zero asserção tocada |

## 3. Homologação real do Organizar

Executado **exatamente um** dispatch autorizado.

```text
cenário                  Organizar
task_type                finance_advice
provider_requested       auto
modelo pelo consumidor   ausente
timeout orquestração     60 s (override só no processo QA)
dispatches               1
retry                    0
segundo provider         0
paralelismo              0
```

Resultado observado:

```text
status              ok
provider_used       mock
fallback_used       true
duration_ms         3523
warning_codes       ["FINANCIAL_DISCLAIMER"]
```

O provider real falhou e o encerramento seguro foi aplicado, exatamente como
projetado: uma única tentativa, sem retry, sem segundo provider, sem chamada
paralela, e resposta pública sem qualquer detalhe técnico.

### 3.1 A causa no lado do provider não pôde ser determinada

A falha produziu `ProviderExecutionError` genérico. O texto do erro existe em
`outcome.error`, mas a projeção de observabilidade vive em **ring buffer na
memória do processo** e foi perdida no teardown; o diagnóstico do runner
(`reportProviderFailures`) não alcançou o PedroCore a tempo
(`diagnóstico indisponível: fetch failed`).

**A assinatura desta falha difere da histórica.** Os timeouts anteriores do
Organizar ficaram em ~30 s e ~60 s; este foi um fallback em 3,5 s. Não é
honesto afirmar que é a mesma limitação já conhecida, nem afirmar qual foi a
causa. O que se sabe é: houve resposta rápida do lado externo, e não expiração
de tempo.

### 3.2 Nenhum defeito local objetivo foi demonstrado

Diagnóstico estrutural executado **contra porta local morta** (`127.0.0.1:9`),
sem nenhum tráfego externo e sem custo:

```text
aiohttp instalado          não  (irrelevante: o SDK usa httpx no caminho async)
cliente construído         Client
client.aio                 AsyncClient
resultado                  httpx.ConnectError — falha limpa e esperada
aclose()                   CONFIRMED
```

Ou seja: construção do cliente, `HttpOptions.timeout`,
`GenerateContentConfig.max_output_tokens`, caminho assíncrono, propagação de
erro e fechamento **funcionam**. A migração async não está quebrada.

Como não existe defeito local objetivo e reproduzível, aplica-se a regra da
frente: **não repetir, não aumentar timeout, não alterar prompt, não alterar
budget, não ativar outro provider, não criar implementação especulativa.**

## 4. Estado final

```text
Assistente IA                   encerrado
Homologação real                3/4
Dívidas                         aprovado
Economizar                      aprovado
Crescer                         aprovado
Organizar                       limitação externa aceita
Gemini                          único provider real ativo
uma IA por requisição           preservada
retry                           inexistente
segundo provider após timeout   bloqueado
fallback real                   default-off
circuit breaker                 default-off
Mock seguro                     preservado
safe mode                       preservado
contrato público da SPA         inalterado
cancelamento local/transporte   reforçado e agora com resultado observado
cancelamento remoto             não comprovável
completion_ambiguous            preservado
```

## 5. QA

```text
suíte integral        721 passed, 7 skipped, 2 warnings
eval harness          14/14, risk_level="none", exit 0
ruff                  aprovado nos arquivos tocados
chamadas reais        1 (a única autorizada)
```

## 6. Limitações finais

1. **Cancelamento remoto continua não comprovável.** Fechar a conexão local —
   mesmo com `transport_close_outcome="confirmed"` — não prova que a geração
   remota parou. `completion_ambiguous` permanece obrigatório.
2. **A causa da falha do Organizar não foi determinada.** A evidência do
   provider vive em memória e não sobreviveu ao encerramento do processo.
3. **A assinatura da falha mudou** em relação ao histórico (3,5 s contra
   ~30 s/~60 s) e isso não foi explicado.
4. **Nenhuma chamada real adicional foi feita** e nenhuma está autorizada.
5. **Os valores de budget continuam conservadores iniciais**, derivados do
   `response_style` das tasks e não de medição de tokens.
6. **Custo real não foi medido.** As métricas de token não chegaram a ser
   observadas numa execução real bem-sucedida.
7. **Persistência de diagnóstico é uma lacuna conhecida de ferramental de QA**,
   não do produto: nada precisa ser implementado no Assistente por causa dela.

## 7. Próximo passo

```text
Nenhuma implementação obrigatória permanece no Assistente IA.
O projeto pode avançar para a próxima frente funcional do FinGuard.
```
