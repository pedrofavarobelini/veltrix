# Etapa 7 — Fallback real controlado

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **mecanismo restrito implementado e validado; default-off e não
operacional com o catálogo real atual**.

## Resultado do gate

| Pergunta | Evidência / veredito |
| --- | --- |
| Timeout prova término da chamada? | não |
| Adapter oferece cancelamento real? | não |
| SDK síncrono usado oferece cancelamento pela integração atual? | não |
| Thread/request pode continuar depois do timeout? | sim, comprovado com `threading.Event` |
| Pode iniciar secundário enquanto a primeira talvez esteja viva? | não; essa classe é excluída |
| Taxonomia separa falha segura e conclusão ambígua? | sim |
| Circuit breaker registra ambiguidade? | sim e abre imediatamente |
| Existe limite global? | sim, dois registros de tentativa no máximo |
| Execução é sequencial? | sim, sem task concorrente ou background |
| Existe allowlist de tasks? | sim |

O gate **não permite fallback após timeout**. Ele permite apenas falhas
estruturadas em que o Veltrix prova simultaneamente:

```text
failure_classification = provider_pre_dispatch
completion_certainty = not_dispatched
external_dispatch = false
```

Hoje isso cobre:

- `ProviderConfigError`, que todos os adapters externos atuais levantam antes
  de criar o cliente ou entrar em `asyncio.to_thread`;
- recusa do circuit breaker entre seleção e aquisição, antes do adapter.

`ProviderExecutionError`, erro genérico, `5xx`, rate limit não caracterizado,
erro interno e `completion_ambiguous` não são elegíveis. Timeout nunca inicia
o secundário.

## Fluxo e limite

O mecanismo só se aplica a `provider=auto` em modo `enforced`:

```text
primário
→ sucesso: encerra
→ falha pre-dispatch comprovada
  → reavalia todos os candidatos, excluindo o primário
  → no máximo um secundário distinto
    → sucesso: encerra
    → qualquer falha: Mock, sem terceiro
```

Não há `gather`, race, hedging, speculative execution, retry em loop ou task em
background. `finished_at` do primário precisa preceder `started_at` do
secundário. Uma sonda mantém trabalho sintético vivo depois de timeout e
comprova que o secundário não começa.

O limite absoluto é de dois providers registrados como tentativas. Como a
única classe que libera o secundário prova que o primário não fez dispatch,
existe no máximo um dispatch externo nesse caminho permitido.

## Seleção do secundário

O motor determinístico é executado novamente com o provider já tentado marcado
como `already_attempted`. O secundário precisa passar novamente por:

- registro, implementação e configuração;
- homologação e autorização estática para auto;
- identidade registrada;
- matriz projeto/papel/ambiente;
- policy e compatibilidade com task;
- catálogo e homologação/autorização do modelo;
- binding total com modelo não nulo;
- safe mode;
- circuito disponível;
- prioridade determinística.

Não há troca para outro modelo do mesmo provider.

## Kill switch e tasks

`PEDROCORE_REAL_FALLBACK_ENABLED` é interno, independente do modo de routing e
default `false`. Payload, metadata e context não o controlam.

A allowlist inicial contém apenas tasks de baixo risco:

- `assistant_chat`;
- `ecosystem_assistant`.

Release gate, finanças, tasks críticas, operações com efeitos externos e todas
as demais tasks ficam fora.

## Auditoria

Cada tentativa registra request/attempt ID, ordinal, provider/modelo, razão da
seleção, início/fim, duração, dispatch, certeza de conclusão, classificação,
estado do circuito, elegibilidade e motivo para iniciar ou bloquear o
secundário. A auditoria registra também a segunda decisão e seus candidatos
eliminados.

Nenhum conteúdo de credencial ou payload sensível é acrescentado.

## Estado operacional real

O catálogo de produção continua com apenas
`gemini + gemini-3.5-flash` homologado e autorizado para auto. Claude, OpenAI,
DeepSeek e Grok não foram homologados por esta etapa.

Assim:

- mecanismo restrito pre-dispatch: implementado;
- fallback real ativo por padrão: não;
- segundo provider real elegível no checkout: não;
- fallback multi-provider operacional: não.

Os testes que exercitam o secundário promovem Claude/OpenAI somente por
`monkeypatch`, com adapters fake, e restauram o catálogo ao terminar.

## Validação

- testes focados da Etapa 7: `17 passed`;
- regressão direcionada conjunta: `103 passed`, sem falha;
- suíte completa: `570 passed, 7 skipped, 2 warnings`;
- eval harness: `14/14`, `risk_level="none"`;
- Ruff nos arquivos alterados: aprovado;
- zero chamadas externas reais;
- nenhuma alteração no FinGuard, frontend, dependências ou `.env`.

## Limites

- timeout continua sem cancelamento e nunca dispara fallback real;
- o circuit breaker continua local por processo;
- a implementação não torna Claude/OpenAI homologados;
- disponibilidade operacional exige outra frente de homologação, sem alterar
  este gate de segurança.

## Nota de evolução — OUTPUT-BUDGET-CANCELLATION-01

Este documento descreve o estado do commit `e389b2c` e permanece válido. A
frente
[[18-provider-output-budget-cancellation/PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]]
migrou o adapter Gemini para cliente assíncrono com timeout de transporte, mas
**não relaxou este gate**:

- timeout de transporte e timeout de orquestração continuam
  `completion_ambiguous`, portanto continuam fora de
  `REAL_FALLBACK_SAFE_CLASSIFICATIONS`;
- truncamento (`MAX_TOKENS`) entrou como `provider_non_retryable`, que também
  não é classificação segura para secundário;
- o fechamento local do transporte é registrado como fato
  (`transport_cancelled_locally`) e **nunca** é tratado como prova de término
  externo.

A tabela original continua correta: o adapter não oferece cancelamento remoto.
