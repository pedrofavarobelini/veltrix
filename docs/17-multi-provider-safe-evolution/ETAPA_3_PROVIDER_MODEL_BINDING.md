# Etapa 3 — Provider/model binding

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **implementado, sem alterar o provider automático**.

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

O catálogo (Etapa 1) continua sendo a única fonte de caracterização. Modelos
não são listados em paralelo: cada `ProviderDefinition` expõe seus
`known_models`, e o catálogo deriva os `ModelDefinition` correspondentes.

Cada modelo pertence a **exatamente um** provider. O identificador conhecido de
cada provider externo é o default declarado no adapter (lido da configuração),
e nenhum outro identificador é inventado.

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
| `MODEL_DEFAULT_UNAVAILABLE` | provider sem default válido (aviso, não bloqueio) |
| `PROVIDER_MODEL_BINDING_INVALID` | binding inválido genérico |

Sem fallback silencioso: quem pede explicitamente uma combinação inválida
recebe bloqueio com o motivo exato, nunca o default no lugar.

## Proteção antes do adapter

`_generate_with_timeout()` deixou de repassar `payload.model`. O adapter recebe
`binding.model_id` — só a combinação aprovada chega até ele. Binding inválido
produz bloqueio (`status=blocked`, `provider_used=none`) antes de qualquer
chamada, comprovado por spy em todos os adapters reais.

## Auditoria e observabilidade

Auditoria distingue `model_requested`, `model_selected` e `model_source`. A
observabilidade acrescenta o bloco `binding` com provider/model solicitado,
selecionado e efetivo. O contrato público de `POST /api/orchestrate` e a
projeção do frontend (`answer`, `suggestions`, `disclaimer`) permanecem
inalterados.

## O que esta etapa NÃO faz

- não altera `AUTO_REAL_PROVIDER_CANDIDATES` (segue `("gemini",)`);
- não ativa Claude/OpenAI no automático;
- não implementa fallback, retry, health, score ou shadow mode;
- não permite que o modelo selecione provider.
