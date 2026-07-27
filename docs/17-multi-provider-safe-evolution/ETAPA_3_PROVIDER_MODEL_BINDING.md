# Etapa 3 — Provider/model binding

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **concluída e corrigida pelo commit `8c97004`, sem alterar o provider
automático**.

## Objetivo

Provider e modelo deixam de ser dois campos independentes: passam a ser
selecionados e validados como **uma unidade coerente**. Combinação
incompatível é rejeitada **antes** de qualquer adapter.

## Onde

- `apps/api/app/modules/provider_catalog/` — `ModelDefinition` e as consultas
  de modelo (`models`, `models_for`, `find_model`, `default_model_for`).
- `apps/api/app/modules/provider_binding/` — `ProviderModelBinding`,
  `SelectedProviderModel` e a resolução do binding.
- `apps/api/app/modules/orchestration/service.py` — binding resolvido antes do
  provider; o adapter recebe apenas o modelo já validado.
- `apps/api/tests/test_provider_model_binding.py` — testes da etapa.

## Fonte única de verdade

Modelos reconhecidos existem apenas no catálogo explícito e imutável
`_MODEL_CATALOG`. Cada `ProviderDefinition.known_models` é uma projeção desse
catálogo; não é a origem dos `ModelDefinition`.

`adapter.default_model`, configuração runtime, posição na lista e `index == 0`
não criam nem homologam modelos. Cada modelo pertence a **exatamente um**
provider, com homologação e autorização declaradas individualmente.

## Estados independentes

```text
modelo configurado
≠ modelo conhecido
≠ modelo homologado
≠ modelo autorizado
```

Provider homologado não homologa seus modelos. Da mesma forma, configuração
runtime não registra, implementa, homologa nem autoriza uma entrada.

## Seleção e validação da configuração

A configuração runtime somente escolhe um identificador candidato. Antes da
execução, o PedroCore valida no catálogo explícito:

- existência e unicidade do identificador/alias;
- provider proprietário;
- registro e implementação;
- homologação e autorização para uso real;
- marcação `default_for_provider`, quando a seleção é do default configurado;
- compatibilidade do provider e do modelo com a task.

Modelo técnico explicitamente solicitado passa pelas mesmas validações, exceto
pela exigência de ser o default do provider. Combinação inválida falha fechada;
o modelo nunca seleciona outro provider.

## Fontes do modelo (`ModelSource`)

| Fonte | Quando |
| --- | --- |
| `provider_default` | default interno declarado do provider externo |
| `explicit_technical` | seleção explícita de ferramenta técnica autorizada |
| `local_fixed` | Mock, `local_qa`, `local_model` |
| `project_policy` | reservado para política por projeto |
| `not_selected` | provider fora do catálogo ou sem default válido |

Consumidor comum nunca determina o modelo. `provider=auto` nunca aceita modelo
do payload.

## Fluxo normal do FinGuard

```
provider=auto + model ausente
→ PedroCore seleciona Gemini (AUTO_REAL_PROVIDER_CANDIDATES, inalterado)
→ PedroCore seleciona o modelo default autorizado do Gemini
→ adapter recebe a combinação já validada
```

## Códigos

| Código | Situação |
| --- | --- |
| `MODEL_UNKNOWN` | modelo não reconhecido pelo catálogo |
| `MODEL_PROVIDER_MISMATCH` | modelo pertence a outro provider |
| `MODEL_NOT_AUTHORIZED` | modelo não homologado para uso real |
| `MODEL_TASK_INCOMPATIBLE` | modelo incompatível com a task |
| `MODEL_NOT_ALLOWED_FOR_CALLER` | consumidor comum enviou modelo |
| `MODEL_NOT_ALLOWED_IN_AUTO` | modelo enviado em `provider=auto` |
| `MODEL_DEFAULT_UNAVAILABLE` | provider sem default configurado válido no catálogo explícito |
| `PROVIDER_MODEL_BINDING_INVALID` | binding inválido genérico |

Sem fallback silencioso: quem pede explicitamente uma combinação inválida
recebe bloqueio com o motivo exato, nunca o default no lugar.

## Binding total antes do adapter

`_generate_with_timeout()` deixou de repassar `payload.model`. O adapter recebe
`binding.model_id` — sempre uma string não vazia já validada. Adapter real não
pode receber `model=None` e não escolhe silenciosamente seu próprio default
depois do binding.

Na ausência de binding válido:

```text
provider=auto
→ Gemini continua sendo o único candidato real
→ nenhum modelo válido
→ zero adapters reais
→ Mock seguro
→ MODEL_DEFAULT_UNAVAILABLE
```

```text
seleção técnica explícita
→ nenhum modelo válido
→ status=blocked
→ provider_used=none
→ zero adapters
```

Não há segunda tentativa com Claude, OpenAI ou outro provider.

## Correção comprovada

As duas falhas confirmadas eram: um `adapter.default_model` arbitrário podia
contaminar a caracterização como se fosse modelo conhecido/homologado; e a
ausência de default válido podia chegar ao adapter real como `model=None`.

As sondas determinísticas agora congelam que:

- default arbitrário não cria nem homologa modelo e resulta em zero chamadas;
- homologação do provider não homologa seu modelo;
- posição no catálogo não determina homologação;
- seleção explícita sem default válido bloqueia antes do adapter;
- `auto` sem default válido usa somente o Mock seguro;
- toda chamada observada a adapter carrega modelo não nulo.

O fechamento da correção registrou `515 passed, 7 skipped`, eval harness
`14/14` e zero chamadas reais.

## Auditoria e observabilidade

Auditoria distingue `model_requested`, `model_selected` e `model_source`. A
observabilidade acrescenta o bloco `binding` com provider/model solicitado,
selecionado e efetivo. O contrato público de `POST /api/orchestrate` e a
projeção do frontend (`answer`, `suggestions`, `disclaimer`) permanecem
inalterados.

## O que esta etapa NÃO faz

- não altera `AUTO_REAL_PROVIDER_CANDIDATES` (segue `("gemini",)`);
- não ativa Claude/OpenAI no automático;
- não implementa fallback entre providers reais, retry, health ou score;
- shadow mode pertence à Etapa 4 e não consome o candidato para execução;
- não permite que o modelo selecione provider.

---

## Navegacao

- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[MOC_FECHAMENTOS]]
