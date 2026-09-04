# Veltrix — Linha do Tempo

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

Como um chat com providers virou um control plane de IA. Cada etapa aqui foi
comprovada pelo Git e pelos documentos de fechamento — não é reconstrução de
memória.

---

## Fase 1 — PedroCore, o produto de interface (V1 → V5.1.9)

Um chat React com backend FastAPI e vários providers. As versões marcavam
entregas visuais: histórico local, feedback, prompts por modo, identidade
visual, responsividade.

Documentos: `Veltrix/10_` a `22_`, `Veltrix/04-comandos/`.
Roadmap da época (histórico): [[../03_ROADMAP]].

## Fase 2 — Replanejamento e MVP backend

`REPLAN-01` reformulou visão, contratos e arquitetura-alvo antes de escrever
código. Depois vieram Task Router, Project Context, Prompt Builder, artefatos
por payload, QA textual e o pipeline central.

- `IMPLEMENT-03` — MVP backend, `POST /api/orchestrate`, safe mode
- tag **`v6.0.0`** — MVP backend
- `IMPLEMENT-04/05` — FinGuard controlado, Artifact Reader, OCR e Playwright
  opt-in
- `FINALIZE-06` — enforcement do release gate, tag **`v7.0.0`**

## Fase 3 — Fundação de inteligência

- `MODEL-FOUNDATION-01` (`689e50a`) — Intelligence Layer, Report Intelligence,
  contrato do Local Model, Evaluation Foundation
- `ECOSYSTEM-INTELLIGENCE-SUITE-01` (`e0ff8e3`) — Report Memory, `local_model`
  opt-in, eval harness

> **É aqui que o study pack antigo parou**, em 09/07/2026. Tudo abaixo é o que
> ele não contava. A auditoria daquele dia está preservada em
> [[PEDROCORE_AUDITORIA_STUDY_MAP_01]].

## Fase 4 — Endurecimento e observabilidade

- `QA-SAFETY-HARDENING-01` (`d6106b7`) — guard estrutural contra provider real
  em testes; eval harness ampliado
- `OBSERVABILIDADE-LOCAL-01` — painel técnico local, store volátil default-off

## Fase 5 — Multi-provider seguro (Etapas 1–7)

A evolução que criou os seis estados de provider:

```text
1 catálogo explícito → 2 identidade e autorização por projeto
→ 3 binding provider+modelo → 4 shadow routing
→ 5 roteamento enforced determinístico → 6 health e circuit breaker
→ 7 fallback real estritamente pre-dispatch
```

Depois, `PROVIDER-OUTPUT-BUDGET-CANCELLATION-01`: orçamento de saída, timeout
de transporte e cliente Gemini assíncrono.

## Fase 6 — Consumers e encerramento do core

- `ENCERRAMENTO-FINAL-01` — assistente IA homologado 4/4
- `STRUCTA-CONSUMER-01` e `ELYRA-ONBOARDING-V1-TEXTUAL` — dois consumers com
  identidade própria e menor privilégio

## Fase 7 — UX V1 e produto V5.2.0

`V1-FINAL-CLOSURE` e `V1-FINAL-UI-FIX`: composer único, Configurações em
drawer, catálogo correto das IAs públicas, modo DEV coerente, ditado por voz,
anexos textuais e a primeira suíte de testes do frontend.

## Fase 8 — Control Plane (Eras 1–10)

A reorganização arquitetural mais profunda do projeto.

| Eras | O que trouxeram |
|---|---|
| 1–2 | baseline auditado e a separação **Runtime Plane / Learning Plane**, verificada por teste |
| 3 | **Universal Contracts V1** — cinco contratos congelados |
| 4–5 | Evidence Platform, Learning Governance V2 |
| 6–7 | resiliência de integração, Dataset Control Plane |
| 8–9 | Evaluation/Training Foundation, Contract Freeze por fingerprint |
| 10 | consolidação — `CONTROL_PLANE_READY` |

Sobre isso vieram as **doze evoluções de plataforma**: Consumer SDK, Policy
Engine, Control Center, Evaluation Plane V2, Model Registry, Shadow Mode,
roteamento explicável, registry de prompts, auditoria correlacionada, SLO,
matriz de compatibilidade e Disaster Recovery com restauração **provada**.

## Fase 9 — O rename

**PedroCore → Veltrix.** A regra: `PedroCore` maiúsculo é marca e virou
Veltrix; `pedrocore` minúsculo é identificador técnico e foi preservado. O corte
por caixa dispensou uma lista de exceções que alguém esqueceria de atualizar.

Um replace cego teria trocado 380 arquivos e quebrado seis contratos
congelados, cinco consumidores e um schema inteiro. Não quebrou nada.

Detalhes: [[../17-veltrix/MIGRACAO_PEDROCORE_VELTRIX]].

## Fase 10 — Risk Engine

V1 (fundação, pré-execução, contrato e gates, pós-execução, histórico) e depois
**V2**: P1–P5 fechados em R0–R5. Em seguida, **Risk Console** e **Project
Registry**.

Estudo: [[VELTRIX_RISK_ENGINE_ESTUDO]].

## Fase 11 — Publicação

`PUBLIC RELEASE GATE`: higienização de watermark, sanitização do histórico Git,
CI verde, grafo documental íntegro, secret scan limpo e Apache-2.0 consistente.
O histórico pré-sanitização ficou em repositório privado separado.

```text
GITHUB PUBLICATION      = CONFIRMED
HUMAN_VISUAL_ACCEPTANCE = PASS
```

## Fase 12 — Final Functional Gate e Freeze

A homologação humana encontrou o último defeito: com o Gemini configurado,
autorizado e selecionado, uma falha externa do provider virava resposta do Mock
apresentada como normal — a interface mentia sobre quem tinha respondido.

A correção usou o contrato que já existia (`allow_mock_fallback`), no boundary
do chat interativo, sem mudar o default para consumers integrados. Junto vieram
as correções finais de UX.

```text
VELTRIX FINALIZATION      = PASS
HUMAN_RUNTIME_ACCEPTANCE  = PASS
VELTRIX FUNCTIONAL FREEZE = ACTIVE
```

Canônico: [[../19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE]].

---

## Os três números que nunca andaram juntos

| Eixo | Onde estava no começo | Onde está hoje |
|---|---|---|
| Produto / UI | V1.0.1 | **V5.2.0** |
| API / backend | — | **0.2.0** |
| Tag Git | `v2.0.0` | **`v7.0.0`** |

A tag `v6.0.0` é o **MVP backend**, não a versão 6 do produto. Confundir os três
eixos é o erro de leitura mais comum na documentação.

## O que mudou de natureza no caminho

O projeto começou perguntando *"como falo com vários providers?"* e terminou
perguntando *"como governo o que uma IA pode fazer antes que ela faça?"*.

O chat continua existindo — mas virou a menor parte.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[PEDROCORE_RESUMO_EXECUTIVO]]
- [[VELTRIX_RISK_ENGINE_ESTUDO]]
- [[../MOC_FECHAMENTOS]]
- [[../08_CHANGELOG]]
