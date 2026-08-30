# PedroCore IA — Versionamento

Atualizado em: 30/08/2026

Licença: **Apache-2.0**.

## Versão atual de produto

V5.1.9

## Versão técnica do backend

0.2.0 (`apps/api/pyproject.toml`) — sem alteração nesta frente.

## Frente atual — Control Plane completo (Eras 1 a 10)

`PEDROCORE-CONTROL-PLANE-01`. Versão técnica do backend permanece `0.2.0`:
não houve breaking change em contrato público.

- Runtime Plane e Learning Plane declarados e verificados por teste (44 módulos).
- Universal Contracts V1 congelados por fingerprint de schema.
- Evidence Platform, Learning Governance V2, resiliência, Dataset Registry e
  Training Foundation implementados.
- `CONTROL_PLANE_READY` + `DATASET_NOT_READY`; `automatic_collection` `Literal[False]`.
- `1340 passed, 21 skipped, 0 failed`; Ruff PASS; build web PASS.
- Outbox e Dataset Registry duráveis, construídos por factory em produção.
- Corrupção degrada e preserva o arquivo; nunca vira store vazio.
- OpenAPI 37 → 39 paths, 156 → 163 schemas, zero breaking change.
- Estado final: [[PedroCore IA/20-control-plane/PEDROCORE_CONTROL_PLANE_FINAL_STATE]].

## Frente anterior — Universal Contracts V1 (Era 3)

`PEDROCORE-UNIVERSAL-CONTRACTS-01`. Versão técnica do backend permanece `0.2.0`:
não houve mudança de contrato público.

- Cinco contratos universais V1 em `apps/api/app/modules/universal_contracts/`.
- Fronteira de autoridade recursiva: consumidor relata fato, nunca emite julgamento.
- Learning Source ≠ Training Candidate; `automatic_collection` permanece `Literal[False]`.
- Quatro acoplamentos por nome de projeto migrados para capability/trait declarativos.
- `1152 passed, 21 skipped, 0 failed` (+55 contract tests); Ruff PASS.
- OpenAPI idêntico byte a byte (37 paths, 156 schemas); grafo 160 documentos/850 links.
- Documento: [[PedroCore IA/20-control-plane/ADR_PEDROCORE_UNIVERSAL_CONTRACTS_V1]].

## Frente anterior — Control Plane (Eras 1 e 2)

`PEDROCORE-CONTROL-PLANE-01`. Versão técnica do backend permanece `0.2.0`:
não houve mudança de contrato público.

- Runtime Plane e Learning Plane declarados em `apps/api/app/architecture/planes.py`.
- Fronteira cobrada por 12 testes em `tests/test_control_plane_boundaries.py`.
- `orchestration` passou a importar a maquinaria do Learning Plane de forma tardia.
- Dataset Foundation permanece exclusiva do PedroCore; `automatic_collection` `Literal[False]`.
- Baseline `1085 passed, 21 skipped` → pós-migração `1097 passed, 21 skipped, 0 failed`.
- Ruff integral PASS; OpenAPI idêntico byte a byte (37 paths); grafo 158 documentos/841 links.
- Zero alteração de banco, migrations, contratos públicos ou frontend.
- Documentos: [[PedroCore IA/20-control-plane/ADR_PEDROCORE_AI_RUNTIME_LEARNING_CONTROL_PLANE]].

## Frente anterior — Elyra Onboarding V1 Textual

`PEDROCORE-ELYRA-ONBOARDING-V1-TEXTUAL`.

- Project Context `elyra`, somente `wellbeing_report_interpretation`.
- Caller Identity `registered`, papel `common_consumer`, origem `elyra`.
- Contratos `elyra-textual-input/v1` e `elyra-textual-output/v1`.
- Mock determinístico no CI; real somente por `provider=auto`, Gemini em
  ambiente não produtivo, sem modelo do caller e sem fallback.
- Correlation e idempotência fail-closed, inclusive duplicata concorrente.
- Multimodal e learning permanecem desabilitados.
- Validação offline: `959 passed, 21 skipped, 2 warnings`; Ruff integral PASS;
  eval `14/14`, `risk_level=none`; grafo 155 documentos/822 links; zero
  chamadas externas.
- Gate: [[PedroCore IA/17-multi-provider-safe-evolution/GATE_PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]].

## Frente anterior — onboarding seguro do Structa

`PEDROCORE-STRUCTA-CONSUMER-01`.

- Project Context `structa`, somente `qa_report_analysis`.
- Caller Identity pelo `PEDROCORE_CALLER_REGISTRY`, com identidade
  `registered` e papel `technical_tool`.
- Gemini autorizado somente em ambiente não produtivo e somente após opt-in
  explícito; demais providers negados.
- `allow_real_provider=false` e fallback real false permanecem defaults.
- Validação offline: `751 passed, 7 skipped, 2 warnings`; zero inferências.
- Gate: [[PedroCore IA/17-multi-provider-safe-evolution/GATE_PEDROCORE_STRUCTA_CONSUMER_01]].

## Frente anterior — ENCERRAMENTO FINAL

`FINGUARD-PEDROCORE-CANONICAL-REPLAY-DOCS-GRAPH-FINALIZE-01`.

```text
PEDROCORE ENCERRADO — CORE OPERACIONAL CONCLUÍDO
```

- Assistente IA do FinGuard **homologado 4/4**: o cenário `Organizar` foi aprovado com Gemini real nesta frente (um único dispatch, `fallback=false`, `retry=0`). Os outros três cenários reaproveitam evidência real anterior já aprovada.
- Validação integral **medida após todas as alterações**: `736 passed, 7 skipped, 2 warnings`; eval `14/14`, `risk_level="none"`, sem chamadas externas reais na suíte.
- Grafo documental Obsidian íntegro: 128 documentos, 697 links resolvidos, zero órfãos, zero links quebrados, validado por `app.modules.docs_graph`.
- Nova capacidade de QA documental: `apps/api/app/modules/docs_graph/` + `tests/test_docs_graph.py`.
- Nenhuma implementação obrigatória restante.

Documento canônico: `PedroCore IA/19-encerramento-final/PEDROCORE_ENCERRAMENTO_FINAL_01.md`.

Vault canônico desde 2026-08-02: `PedroCore IA/`. A reorganização preservou
127/127 documentos anteriores; ver
`PedroCore IA/MANIFESTO_REORGANIZACAO_20260802.md`.

## Frente anterior (HISTÓRICO)

`PEDROCORE-MULTI-PROVIDER-DOCS-CONSOLIDATION-01`: fechamento documental das Etapas 1–7 da evolução multi-provider segura, tomando `e389b2c` como último commit de implementação. Catálogo, identidade/autorização, binding, shadow, enforced, health/circuit breaker e fallback pre-dispatch concluídos. Naquele momento a validação integral era `570 passed, 7 skipped, 2 warnings`. A arquitetura multi-provider está concluída; multi-provider automático operacional ainda não, pois somente `gemini + gemini-3.5-flash` está homologado e elegível.

Projeto **finalizado localmente**: `PEDROCORE-IMPLEMENT-05` (05A–05F, integrações reais controladas) e `PEDROCORE-FINALIZE-06` (06A enforcement final + 06B fechamento) concluídas. Tag final local: `v7.0.0`. Ver `PedroCore IA/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md`.

DOCFIX anterior: saneamento documental/Obsidian, sem alteração de código de produção, testes, tags, merge ou push. Mapeamento central: `PedroCore IA/00_MAPEAMENTO_GERAL_PEDROCORE.md`.

Frente anterior: `PEDROCORE-MODEL-FOUNDATION-01` — fundação de inteligência própria, commitada em `689e50a`. Testes na época: `257 passed, 6 skipped, 2 warnings`. Ver `PedroCore IA/13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01.md`.

Checkpoint histórico: `PEDROCORE-QA-SAFETY-HARDENING-01` — endurecimento QA/safety commitado em `d6106b7`. Naquele checkpoint: Pytest `341 passed, 6 skipped, 2 warnings`; eval harness `14/14 passed`, `risk_level="none"`. Ver `PedroCore IA/16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01.md`.

Frente documental anterior: `PEDROCORE-DOCS-GRAPH-LINKING-01` — linkagem Markdown/Obsidian em documentação, sem alteração de código.

O histórico de `FINGUARD-PEDROCORE-ASSISTANT-REAL-PROVIDER-QA-01` permanece registrado no changelog; o contrato comum atual do consumidor é `provider=auto` sem modelo, com decisão final no PedroCore.

## Status atual

`PEDROCORE-REPLAN-01` (01A a 01E) concluída no escopo documental. `PEDROCORE-IMPLEMENT-01A/01B` commitada em `577bc88`; `01C–01H` commitada em `95cbfab`; `PEDROCORE-IMPLEMENT-02` commitada em `e115672`. `PEDROCORE-IMPLEMENT-03` (MVP backend Blocos 1–7) commitada em `6ed4c41`: QA textual real por heurística local determinística, release gate conservador com `blocked_reason`, endpoint `POST /api/orchestrate` (pipeline centralizado, também usado por `/api/chat`), safe mode com `allow_real_provider=false` por padrão, autenticação interna opcional para `/api/orchestrate`, contrato padronizado de warnings/errors e audit não persistente completo. `PEDROCORE-FINALIZE-04` foi consolidada em `ee2ac68`, commit para o qual aponta a tag anotada `v6.0.0` com a mensagem `v6.0.0 - MVP backend PedroCore IA`. Testes backend passando (`125 passed, 2 warnings`). Sem alterações de frontend, design, providers reais ou `.env`.

## Tags atuais

`v7.0.0` é a tag final local do core operacional seguro e aponta para `33b2c0489c19776ef460fc85dea3c24298b46a3c`.

`v6.0.0` existe e aponta para `ee2ac68679feea6ac108abba8726d11da101576c` (`ee2ac68`). A tag representa o fechamento do MVP backend; ela não é a tag final local atual.

Resumo:

- `v6.0.0` = MVP backend.
- `v7.0.0` = fechamento técnico local do core operacional seguro.
- `d6106b7` = `PEDROCORE-QA-SAFETY-HARDENING-01`, hardening QA/safety posterior ao fechamento local.
- `62beff1` a `e389b2c` = Etapas 1–7 e correções da evolução multi-provider segura.
- Pendência obrigatória de código/teste/Git = zero no estado final registrado.
- Pendência operacional multi-provider = homologar um segundo provider/modelo real em frente separada.

## Observação sobre versionamento

Existem duas numerações distintas no projeto, que não devem ser confundidas:

- **Versão de produto** (V5.1.9): marca entregas visuais/funcionais de frontend.
- **Versão técnica do backend** (`0.2.0`): versão do pacote Python da API.

Nenhuma das duas foi alterada por `PEDROCORE-REPLAN-01` (01A a 01E).

## Próximos passos (opcionais, pós-fechamento)

- Homologar um segundo provider/modelo real em frente separada, escolhendo Claude ou OpenAI mediante decisão explícita.
- Push para GitHub/portfólio e deploy — decisões humanas futuras.
- Execução real de OCR/multimodal/Playwright somente com flags, dependências instaladas manualmente e revisão humana.
- Saneamento adicional de documentos históricos duplicados dentro de `PedroCore IA/`, se o usuário quiser reduzir ruído do vault.
- Bloco 12 (dashboard/logs/admin): cancelado por decisão de produto — não é pendência.
