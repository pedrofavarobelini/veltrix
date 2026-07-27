# PedroCore Multi-Provider Safe Evolution — Fechamento das Etapas 1–7

Frente documental: `PEDROCORE-MULTI-PROVIDER-DOCS-CONSOLIDATION-01`.

Base técnica auditada: `e389b2c` (`feat: adicionar fallback real controlado`),
em 26/07/2026.

## 1. Resumo executivo

Esta evolução transformou um registry com vários adapters, mas com decisão
automática real congelada no Gemini, em uma arquitetura de orquestração
multi-provider explícita, determinística, auditável e fail-closed.

Antes das Etapas 1–7:

- providers externos existiam no registry, mas não havia catálogo técnico
  separado de configuração;
- a identidade podia depender demais da origem declarada;
- provider e modelo ainda podiam chegar ao adapter sem um binding total;
- não havia motor único `legacy`/`shadow`/`enforced`;
- não havia health state, circuit breaker nem fallback real controlado.

Depois das Etapas 1–7, o PedroCore possui catálogo de providers/modelos,
identidade por credencial, autorização por projeto, binding total, política
determinística, routing enforced, circuit breaker e fallback restrito a falhas
comprovadamente anteriores ao dispatch.

> Arquitetura multi-provider: concluída.
>
> Multi-provider automático operacional: não.
>
> Motivo: somente um provider/modelo externo está homologado e elegível.
>
> Próximo passo: homologar um segundo provider real em frente separada.

O motor não cria homologação. Claude, OpenAI, DeepSeek e Grok continuam
conhecidos e implementados estruturalmente, mas não homologados nem autorizados
para o automático.

## 2. Fluxo atual completo

```text
Sistema consumidor
→ autenticação do caller
→ identidade derivada da credencial
→ validação de origin_system como alegação
→ classificação da tarefa
→ policy e safe mode
→ autorização projeto/papel/ambiente/provider
→ catálogo explícito de provider e modelo
→ binding provider/modelo
→ decisão legacy/shadow/enforced
→ health state e circuit breaker
→ seleção de exatamente um candidato
→ execução do adapter
→ classificação da conclusão ou falha
→ secundário somente se pre-dispatch seguro; caso contrário Mock
→ normalização da resposta
→ QA textual e release gate
→ auditoria e observabilidade
→ contrato uniforme ao consumidor
```

Fluxo normal:

```text
caller
→ identidade
→ policy
→ binding
→ routing
→ circuit
→ provider
→ QA
→ resposta
```

Fluxo de timeout:

```text
provider dispatch
→ timeout da espera
→ completion_ambiguous
→ a thread pode continuar
→ circuito atualizado
→ Mock seguro
→ nenhum secundário
```

Fluxo de fallback permitido:

```text
primário selecionado
→ falha comprovadamente pre-dispatch
→ primeiro provider marcado como already_attempted
→ secundário distinto passa novamente por todos os filtros
→ uma tentativa sequencial
→ sucesso ou Mock
→ terceiro provider proibido
```

## 3. Princípios preservados

- PedroCore permanece o orquestrador central do ecossistema.
- FinGuard chama somente o PedroCore; não recebe chaves de provider.
- Consumidores comuns usam `provider=auto`.
- Consumidores comuns não escolhem modelo.
- `origin_system` é alegação validada, não identidade soberana.
- Chaves e headers completos não entram em auditoria ou resposta.
- O frontend não recebe metadados técnicos de routing.
- Execução normal usa uma IA; fallback permitido é estritamente sequencial.
- Não há ensemble, votação, A/B, hedging ou comparação de respostas.
- Não há execução paralela de providers.

## 4. Linha do tempo das etapas e correções

### Etapa 1 — catálogo e caracterização

- **Problema:** adapter registrado, chave configurada e provider homologado
  ainda eram conceitos fáceis de confundir.
- **Objetivo:** representar providers e modelos por estados separados.
- **Implementação:** `provider_catalog`, tipos, invariantes e snapshot sem
  segredos.
- **Testes:** `test_provider_catalog.py` e
  `test_provider_auto_characterization.py`.
- **Commit:** `62beff1 — feat: caracterizar catalogo seguro de providers`.
- **Resultado:** catálogo multi-provider estrutural criado sem mudar execução.
- **Limite remanescente naquele checkpoint:** routing ainda era Gemini-only.

### Etapa 2 — identidade e autorização por projeto

- **Problema:** autorização de provider não podia depender apenas do payload.
- **Objetivo:** derivar identidade da credencial e negar por padrão.
- **Implementação:** `caller_identity`, `provider_authorization`, matriz por
  identidade/projeto/papel/ambiente/provider e auditoria aditiva.
- **Testes:** `test_caller_identity_authorization.py` e regressões de
  observabilidade.
- **Commit:** `64e6c59 — feat: autorizar providers por identidade de projeto`.
- **Resultado:** provider real passou a exigir autorização cumulativa.
- **Limite encontrado:** a chave global compartilhada ainda ganhava privilégio
  indevido, corrigido imediatamente no fix seguinte.

### Fix — credencial compartilhada

- **Problema confirmado:** a chave global podia receber papel técnico, alegar
  `origin_system=finguard`, assumir `project_id=finguard` e alcançar Gemini.
- **Objetivo:** separar autenticação de identificação inequívoca.
- **Implementação:** `identity_strength`, identidade `ambiguous`, papel
  `common_consumer`, projeto `shared_or_unknown` e ausência total de regra real.
- **Testes:** sonda regressiva com spy, autorização, policy, observabilidade e
  `test_shared_credential_privilege.py`.
- **Commit:** `c67ec6a — fix: bloquear provider real para credencial compartilhada`.
- **Resultado:** credencial compartilhada autentica, mas não identifica projeto
  nem autoriza provider real.
- **Limite remanescente:** credenciais distintas ainda precisam ser
  provisionadas fora do repositório.

### Etapa 3 — provider/model binding

- **Problema:** provider e modelo podiam ser tratados como escolhas separadas.
- **Objetivo:** validar a combinação como unidade antes do adapter.
- **Implementação:** `provider_binding`, `SelectedProviderModel`,
  `ProviderModelBinding` e `ModelSource`.
- **Testes:** `test_provider_model_binding.py` e regressões de policy/audit.
- **Commit:** `be56a7e — feat: vincular providers e modelos com seguranca`.
- **Resultado:** consumidor comum não envia modelo; ferramenta técnica só usa
  modelo conhecido e compatível.
- **Limite encontrado:** defaults runtime ainda podiam contaminar a noção de
  modelo reconhecido e permitir `model=None`.

### Etapa 4 — shadow routing

- **Problema:** não existia forma segura de observar uma política futura.
- **Objetivo:** calcular candidato sem mudar a execução.
- **Implementação:** filtros eliminatórios, prioridade estática e desempate pelo
  primeiro sobrevivente.
- **Testes:** `test_shadow_routing.py`, inclusive efeito nulo.
- **Commit:** `d93a4ff — feat: adicionar politica shadow de providers`.
- **Resultado:** decisão planejada passou a ser auditável sem segunda IA.
- **Limite remanescente naquele checkpoint:** shadow não controlava execução.

### Fix — homologação e configuração de modelos

- **Problema A:** `adapter.default_model` podia ser interpretado como modelo
  conhecido e homologado.
- **Problema B:** ausência de default válido podia chegar como `model=None` e
  deixar o adapter escolher silenciosamente.
- **Objetivo:** tornar o catálogo explícito a única fonte de modelos.
- **Implementação:** `_MODEL_CATALOG`, homologação individual, validação do
  default e binding fail-closed antes do adapter.
- **Testes:** catálogo, binding, shadow, autorização, observabilidade e smoke
  Gemini com fakes.
- **Commits:** `8c97004 — fix: separar homologacao e configuracao de modelos` e
  `0daa34b — docs: reconciliar binding explicito de modelos`.
- **Resultado:** configuração só seleciona identificador; não cria, registra,
  homologa nem autoriza modelo. Adapter real nunca recebe `model=None`.
- **Limite remanescente:** somente o modelo Gemini estava homologado.

### Etapa 5 — routing enforced com chamada única

- **Problema:** shadow observava, mas não controlava o candidato automático.
- **Objetivo:** aplicar o mesmo motor sem duplicar decisões.
- **Implementação:** modos internos `legacy`, `shadow` e `enforced`, rollback
  seguro para `legacy` e primeiro sobrevivente determinístico.
- **Testes:** `test_provider_routing_enforced.py`; `147 passed` direcionados e
  `529 passed, 7 skipped, 2 warnings` na suíte daquele checkpoint.
- **Commit:** `f7afff8 — feat: aplicar roteamento automatico com chamada unica`.
- **Resultado:** enforced executava no máximo uma tentativa real; falha usava
  Mock, sem secundário.
- **Limite remanescente:** nenhum segundo provider/modelo homologado.

### Etapa 6 — health state e circuit breaker

- **Problema:** falhas não possuíam estado técnico isolado por destino.
- **Objetivo:** impedir novas aquisições quando a evidência atribuível ao
  provider justificasse.
- **Implementação:** `closed/open/half_open`, chave
  `ambiente + provider + modelo`, threshold, cooldown monotônico, probe único e
  lock por processo.
- **Testes:** `test_provider_health_circuit_breaker.py`; `176 passed`
  direcionados e `553 passed, 7 skipped, 2 warnings` no checkpoint.
- **Commit:** `30d308f — feat: adicionar health state e circuit breaker`.
- **Resultado:** circuit open elimina candidato antes do adapter; timeout
  ambíguo abre imediatamente quando a feature está habilitada.
- **Limites:** default-off, memória local e nenhuma coordenação multiprocesso.

### Etapa 7 — fallback real controlado

- **Problema:** um secundário poderia sobrepor uma chamada cujo timeout só
  cancelou a espera.
- **Objetivo:** permitir secundário apenas quando não houve dispatch externo.
- **Implementação:** kill switch interno, allowlist de tasks, classificação
  pre-dispatch, reavaliação integral, máximo de dois registros e fluxo sem loop.
- **Testes:** `test_provider_real_fallback_controlled.py`; `17 passed` focados,
  `103 passed` direcionados e `570 passed, 7 skipped, 2 warnings` na suíte final.
- **Commit:** `e389b2c — feat: adicionar fallback real controlado`.
- **Resultado:** secundário só pode iniciar após prova
  `provider_pre_dispatch + not_dispatched + external_dispatch=false`.
- **Limite operacional:** default-off e sem segundo provider homologado.

## 5. Etapa 1 — catálogo atual

Estados de provider não são sinônimos:

```text
registered
≠ implemented
≠ configured
≠ homologated
≠ authorized_for_auto
≠ health
```

| Provider externo | Modelo explícito | Provider homologado | Modelo homologado/autorizado | Auto |
| --- | --- | ---: | ---: | ---: |
| `gemini` | `gemini-3.5-flash` | sim | sim | sim |
| `claude` | `claude-sonnet-4-5` | não | não | não |
| `openai` | `gpt-5.2-mini` | não | não | não |
| `deepseek` | `deepseek-chat` | não | não | não |
| `grok` | `grok-4.3` | não | não | não |

Mock e `local_qa` são internos, não providers externos. `local_model` é
generativo local, default-off e não homologado como provider externo.

## 6. Etapa 2 — identidade e autorização

Identidade registrada é derivada desta sequência:

```text
credencial registrada
→ credential_id não secreto
→ project_id
→ caller_role
→ environment
→ allowed_origins
```

`origin_system` permanece no payload para contexto e compatibilidade, mas é
validado contra a identidade. A matriz é fail-closed:

```text
identity_strength + project_id + caller_role + environment + provider
→ allowed ou denied
```

Consumidor comum pode pedir `auto`, `mock`, `local` ou `local_qa`. Não pode
escolher provider externo nem modelo.

## 7. Fix da credencial compartilhada

Vulnerabilidade original:

```text
chave global
→ technical_tool
→ origin_system=finguard
→ project_id=finguard
→ Gemini alcançado
```

Estado corrigido:

```text
identity_strength=ambiguous
caller_role=common_consumer
project_id=shared_or_unknown
origin_system=not_trusted
→ nenhum provider real
```

Regra conceitual:

```text
autenticado
≠ identificado
≠ autorizado
```

## 8. Etapa 3 — provider/model binding

Provider e modelo são uma unidade. O binding verifica catálogo, proprietário,
registro, implementação, homologação, autorização, default e compatibilidade
com a task antes de qualquer adapter.

- Consumidor comum não envia modelo.
- Ferramenta técnica pode selecionar somente combinação válida.
- Modelo nunca escolhe provider.
- Binding inválido bloqueia ou usa Mock conforme o modo.
- Adapter real recebe `binding.model_id`, sempre string não vazia.

## 9. Fix de homologação e configuração de modelos

Falha A:

```text
adapter.default_model
→ modelo conhecido
→ modelo homologado
```

Falha B:

```text
binding sem modelo válido
→ model=None
→ adapter escolhia default
```

Correção:

- `_MODEL_CATALOG` é explícito e imutável;
- configuração runtime só seleciona identificador candidato;
- homologação é individual por modelo;
- default precisa existir, pertencer ao provider e estar marcado;
- binding inválido não chama adapter;
- posição em lista ou `index == 0` não cria homologação.

## 10. Etapa 4 — shadow routing

O shadow calcula:

```text
filtros eliminatórios
→ prioridade estática por projeto/task
→ primeiro sobrevivente
→ comparação de identificadores com o efetivo
```

Ele registra candidatos considerados/eliminados e motivo. Em modo `shadow`, a
decisão não controla execução e não chama uma segunda IA. O circuit state atual
é consultado somente como filtro eliminatório, nunca como score.

## 11. Etapa 5 — enforced routing

`PEDROCORE_PROVIDER_ROUTING_MODE` aceita:

| Modo | Comportamento |
| --- | --- |
| `legacy` | preserva a seleção anterior; default conservador |
| `shadow` | calcula e registra, sem controlar execução |
| `enforced` | aplica o primeiro candidato elegível |

Valor inválido recua para `legacy`. Payload não controla o modo. Shadow e
enforced usam o mesmo motor, sem duplicação. O enforced continua limitado ao
Gemini porque os demais candidatos falham nos filtros de homologação/autorização.

## 12. Etapa 6 — health e circuit breaker

State machine:

```text
closed
→ provider_retryable até threshold: open
→ completion_ambiguous: open imediato

open
→ cooldown monotônico: half_open

half_open
→ um probe por processo
→ success: closed
→ qualquer não sucesso: open
```

- Chave: `environment + provider_id + model_id`.
- Threshold default: 3.
- Cooldown default: 30 segundos.
- Clock: `time.monotonic`.
- Concorrência: `threading.RLock`.
- Persistência: nenhuma.
- Coordenação entre workers/instâncias: nenhuma.
- Ativação: `PEDROCORE_CIRCUIT_BREAKER_ENABLED`, default `false`.

## 13. Etapa 7 — fallback controlado

Fallback real só se aplica a `provider=auto` em modo `enforced`, com
`PEDROCORE_REAL_FALLBACK_ENABLED=true` e task na allowlist
`assistant_chat`/`ecosystem_assistant`.

O primário só é elegível para fallback quando a tentativa prova:

```text
failure_classification=provider_pre_dispatch
completion_certainty=not_dispatched
external_dispatch=false
```

O secundário deve ser diferente, não tentado, homologado, autorizado,
configurado, compatível, ter binding válido e circuito disponível. Ele passa
novamente por todos os filtros e pela prioridade determinística.

Não há fallback após timeout, `ProviderExecutionError`, erro interno, caller,
policy, autorização, binding, modelo, payload ou safe mode. Não há terceiro
provider. O máximo é de dois registros de provider; no caminho permitido o
primário não fez dispatch, portanto há no máximo um dispatch externo.

## 14. Taxonomia de falhas

Nomes exatos de `FailureClassification`:

| Classificação | Significado / uso |
| --- | --- |
| `success` | tentativa concluída com sucesso |
| `provider_retryable` | falha atribuível ao provider; degrada health |
| `provider_non_retryable` | falha atribuível, mas não retryable |
| `provider_pre_dispatch` | falha antes de qualquer dispatch externo |
| `completion_ambiguous` | espera terminou sem prova de término externo |
| `caller_error` | erro do caller; não contamina health |
| `policy_error` | bloqueio de policy; não contamina health |
| `internal_error` | erro interno; não é seguro para fallback |

`CompletionCertainty` usa `not_dispatched`, `completed` e `ambiguous`.

## 15. Auditoria e observabilidade

A auditoria não persistente distingue:

- credencial/identidade autenticada e `identity_strength`;
- projeto autenticado, papel, ambiente e origem declarada;
- provider/modelo solicitado, selecionado e efetivo;
- autorização e motivo;
- binding e `model_source`;
- decisão shadow e diferença para o efetivo;
- routing mode, política, candidatos e eliminação;
- IDs, ordinal, horários e duração de cada tentativa;
- circuit state antes/depois e probe half-open;
- dispatch, completion certainty e failure classification;
- fallback eligibility, motivo e candidatos secundários.

Não entram API key, token, header completo ou conteúdo sensível desnecessário.

## 16. Segurança

- Credencial compartilhada não alcança provider real.
- Modelo arbitrário é bloqueado antes do adapter.
- Configuração não cria homologação.
- Binding inválido não chega ao adapter.
- `allow_real_provider=false` preserva safe mode.
- Matrizes e catálogos negam por padrão.
- Timeout ambíguo nunca dispara secundário.
- Circuit breaker e fallback são default-off.
- Não há execução paralela de providers.
- Não há terceira tentativa.
- Mock seguro encerra falhas sem expor detalhes técnicos na resposta pública.

> **Evolução posterior.** A frente
> [[18-provider-output-budget-cancellation/PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]]
> acrescentou orçamento de saída, timeout de transporte e cliente Gemini
> assíncrono. Todas as garantias listadas acima permanecem: timeout continua
> ambíguo, sem retry, sem secundário, sem paralelismo, sem terceira tentativa.
> O cancelamento local e o de transporte passaram a ser reais; o cancelamento
> **remoto** continua não comprovável.

## 17. Compatibilidade FinGuard

Contrato de consumo:

```text
FinGuard
→ provider=auto
→ model ausente
→ PedroCore controla identidade, policy, provider, modelo e fallback
```

O frontend recebe somente:

```text
answer
suggestions
disclaimer
```

FinGuard não recebe chave nem metadados internos de routing. Não existe
evidência de que o FinGuard esteja usando um segundo provider real. Provider
real exige credencial registrada, safe mode liberado e todos os demais gates.

## 18. Testes

Fechamento confirmado na Etapa 7:

```text
570 passed
7 skipped
2 warnings preexistentes
eval harness 14/14
risk_level=none
```

Cobertura acumulada relevante:

- invariantes e snapshots do catálogo;
- identidade registrada, ambígua e spoofing de origem;
- matriz de autorização;
- binding total e modelo não nulo;
- shadow sem efeito;
- enforced com chamada única;
- closed/open/half-open, cooldown e probe concorrente;
- timeout com thread ainda viva;
- fallback somente pre-dispatch;
- kill switch e allowlist de tasks;
- máximo de dois registros, sem terceiro e sem sobreposição;
- auditoria/observabilidade e contrato FinGuard;
- zero chamadas externas nas suítes desta evolução.

Os dois warnings conhecidos são depreciações de Pydantic class config e
Starlette/httpx. Esta frente documental não reexecutou a suíte, pois não alterou
código ou testes.

## 19. Estado operacional atual

| Capacidade | Implementada | Ativa por padrão | Operacional |
| --- | ---: | ---: | ---: |
| Catálogo multi-provider | sim | sim | sim |
| Identidade por credencial registrada | sim | depende de provisionamento | parcial |
| Provider/model binding | sim | sim | sim |
| Shadow routing | sim | não | disponível |
| Enforced routing | sim | conforme configuração | limitado ao Gemini |
| Circuit breaker | sim | não | disponível por processo |
| Fallback real | sim | não | sem secundário elegível |
| Multi-provider automático | sim estruturalmente | não | não |

Distinções obrigatórias:

```text
implementado
≠ configurado
≠ homologado
≠ autorizado
≠ habilitado
≠ operacional
```

## 20. O que falta para um segundo provider

1. Decidir formalmente entre Claude e OpenAI.
2. Confirmar/registrar explicitamente o modelo escolhido.
3. Homologar o provider.
4. Homologar e autorizar o modelo.
5. Autorizar o provider para projeto, papel e ambiente.
6. Provisionar credencial registrada e distinta para o FinGuard.
7. Executar smoke real manual e opt-in, com autorização própria.
8. Validar resposta, normalização, erro e timeout sem expor segredos.
9. Ativar `enforced` em QA.
10. Observar auditoria e comportamento operacional.
11. Ativar circuit breaker de forma gradual.
12. Somente depois avaliar a ativação do fallback.

## 21. Próxima frente recomendada

A escolha ainda não está formalizada. A próxima frente deve ser uma destas:

```text
PEDROCORE-PROVIDER-HOMOLOGATION-CLAUDE-01
```

ou:

```text
PEDROCORE-PROVIDER-HOMOLOGATION-OPENAI-01
```

Não iniciar ambas nem escolher silenciosamente. Homologação precisa de escopo,
credencial, smoke real opt-in, critérios de sucesso/erro/timeout e rollback
próprios.

## Links relacionados

- [[../MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[ETAPA_1_CATALOGO_PROVIDERS]]
- [[ETAPA_2_IDENTIDADE_AUTORIZACAO]]
- [[FIX_CREDENCIAL_COMPARTILHADA]]
- [[ETAPA_3_PROVIDER_MODEL_BINDING]]
- [[FIX_HOMOLOGACAO_CONFIGURACAO_MODELOS]]
- [[ETAPA_4_SHADOW_MODE]]
- [[ETAPA_5_ROTEAMENTO_AUTOMATICO_CHAMADA_UNICA]]
- [[ETAPA_6_HEALTH_STATE_CIRCUIT_BREAKER]]
- [[ETAPA_7_FALLBACK_REAL_CONTROLADO]]
- [[../09_STATUS_ATUAL]]
- [[../03-versoes/ROADMAP]]
- [[../08_CHANGELOG]]
