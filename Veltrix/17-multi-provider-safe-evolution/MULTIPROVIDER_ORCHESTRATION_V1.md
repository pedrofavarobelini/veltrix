# MULTIPROVIDER-ORCHESTRATION-V1 — candidatos do auto derivados do catálogo

Frente conjunta Veltrix + Elyra, 01/10/2026. Base: `feat/elyra-multimodal-v2`
(`53170c4`). Branch de trabalho: `feat/multiprovider-orchestration-v1`
(**não conectada ao Railway, não mergeada, sem deploy**).

## Veredito

| Item | Estado |
|---|---|
| Arquitetura multi-provider (Etapas 1–7) | preservada, sem simplificação |
| Auto routing engine | candidatos derivados do catálogo; sem tupla fixa |
| Gemini | homologado, autorizado no auto (inalterado) |
| Claude / OpenAI / Grok / DeepSeek | **não homologados** — `PENDING_REAL_SMOKE` |
| Elyra provider-agnostic | sim (ADR-0034 da Elyra, reaplicada sobre a Stage 29 em `feat/elyra-provider-agnostic-current`) |
| `REAL_PROVIDER_INTERNET_EXPOSURE` | **BLOCKED** |
| Deploy real | **NOT EXECUTED**; chamadas externas reais: **0** |

## Problema real encontrado

A arquitetura já existia e, em `enforced`, já selecionaria um segundo provider
homologado. O que impedia "homologar sem editar código" era:

1. `AUTO_REAL_PROVIDER_CANDIDATES = ("gemini",)` como fonte do modo `legacy`
   (default) e do candidato do binding;
2. o motor só considerava `("gemini", "claude", "openai")`: DeepSeek e Grok
   nunca eram avaliados, nem para serem eliminados;
3. nenhum filtro de capability;
4. `/api/providers` derivava "auto configurado" de `gemini.is_configured`.

## O que mudou

- `auto_real_provider_candidates()` = `provider_catalog_service.authorized_auto_ids()`;
- `routing_candidate_ids()` = todos os providers externos reais do catálogo,
  em `static_priority`; listas por projeto/task apenas **ordenam**;
- `EliminationReason.CAPABILITY_MISSING`; capability exigida por task (default
  `text_generation`), lida do catálogo explícito;
- `POLICY_VERSION = "static-priority-v3"`.

Nada mudou em: homologação, matriz de autorização, default `legacy`, circuit
breaker, fallback (allowlist, só pre-dispatch, máximo 2), timeout ambíguo.

> Multi-provider automático requer `PEDROCORE_PROVIDER_ROUTING_MODE=enforced`.
> Em `legacy`, o primeiro candidato configurado do catálogo é o único avaliado e
> negação nunca promove outro provider.

## Testes

`test_multiprovider_auto_routing.py` (19, fakes, pelo contrato Elyra real):
A consumer não escolhe provider/modelo · B só Gemini → Gemini, demais
`not_homologated` · C1 ordem do catálogo · C2 preferência projeto/task →
Claude, contrato Elyra OK · C3/C4 capability · C5 legacy não promove ·
D configurado ≠ homologado · E homologado sem matriz `elyra` · F modelo não
homologado · G circuit open antes do adapter e por modelo/ambiente ·
H não configurado contornado sem dispatch; falha Elyra sem secundário ·
I timeout ambíguo sem segundo dispatch.

Suíte: `2091 passed, 62 skipped, 2 warnings` (base `2072`). 4 dos 19 falham
no código anterior — os demais já passavam, confirmando que o motor existia.

## Segurança antes de provider real

`/api/chat` e `/api/providers` sem autenticação; `/docs` ligado; sem limite de
payload nem rate limit; chave interna compartilhada comparada com `!=`;
gate de observabilidade depende de `FORWARDED_ALLOW_IPS`. Com caller registry
configurado, `/api/chat` não alcança provider real (identidade `ambiguous`).
Gate `BLOCKED` até private networking **ou** hardening comprovado.

## Homologação de um provider (processo)

adapter existe → chave no Veltrix → modelo no `_MODEL_CATALOG` → testes de
contrato e de adapter com fake → erro/timeout → **smoke real opt-in separado**
→ `homologation=HOMOLOGATED_REAL` + `authorized_for_auto=True` + modelo
`homologated/authorized` → regra na matriz por projeto → elegível ao auto.
Para `elyra`, revisão de suboperador/consentimento pelo owner antes da regra.

## Links

- [[FECHAMENTO_ETAPAS_1_A_7]]
- [[../MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
