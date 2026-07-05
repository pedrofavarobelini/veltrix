# PedroCore IA — Versionamento

Atualizado em: 04/07/2026

## Versão atual de produto

V5.1.9

## Versão técnica do backend

0.2.0 (`apps/api/pyproject.toml`) — sem alteração nesta frente.

## Frente atual

PEDROCORE-IMPLEMENT-01C/01D/01E/01F/01G/01H — Base interna de orquestração expandida.

## Status atual

`PEDROCORE-REPLAN-01` (01A a 01E) concluída no escopo documental (commits `1e5a8cb`, `6e7badd`, `c1e7816`, `8c68b67`, `cc808a7`). `PEDROCORE-IMPLEMENT-01A/01B` (Task Router mínimo) commitada em `577bc88`. Nesta etapa: Project Context mínimo, Prompt Builder mínimo, metadados estruturais no `ChatResponse` e audit metadata não persistente. Testes backend passando (`37 passed, 2 warnings`). `PEDROCORE-IMPLEMENT-01I` (Orchestration module) avaliada e adiada. Sem alterações de frontend, design, providers reais ou `.env`.

## Observação sobre versionamento

Existem duas numerações distintas no projeto, que não devem ser confundidas:

- **Versão de produto** (V5.1.9): marca entregas visuais/funcionais de frontend.
- **Versão técnica do backend** (`0.2.0`): versão do pacote Python da API.

Nenhuma das duas foi alterada por `PEDROCORE-REPLAN-01` (01A a 01E).

## Próximos passos técnicos

- QA Intelligence real (parser de relatório, classificador de risco), consumindo o Prompt Builder e o Project Context já existentes (ainda não implementada).
- Artifact Reader real (ainda não implementado).
- Orchestration module e/ou endpoint `/api/orchestrate` — avaliados e adiados nesta etapa (`01I`).
- Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`, seção 12, para o escopo completo de `PEDROCORE-IMPLEMENT-01`.
