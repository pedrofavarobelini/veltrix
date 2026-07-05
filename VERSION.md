# PedroCore IA — Versionamento

Atualizado em: 05/07/2026

## Versão atual de produto

V5.1.9

## Versão técnica do backend

0.2.0 (`apps/api/pyproject.toml`) — sem alteração nesta frente.

## Frente atual

PEDROCORE-IMPLEMENT-02A/02B/02C/02D/02E/02F/02G — QA textual foundation.

## Status atual

`PEDROCORE-REPLAN-01` (01A a 01E) concluída no escopo documental (commits `1e5a8cb`, `6e7badd`, `c1e7816`, `8c68b67`, `cc808a7`). `PEDROCORE-IMPLEMENT-01A/01B` commitada em `577bc88`; `PEDROCORE-IMPLEMENT-01C/01D/01E/01F/01G/01H` commitada em `95cbfab`. Nesta etapa: policy de `allowed_tasks`, artefatos textuais por payload, Prompt Builder com artefatos e QA response skeleton seguro (sem análise real, `can_advance` sempre `False`). Testes backend passando (`66 passed, 2 warnings`). Sem alterações de frontend, design, providers reais ou `.env`.

## Observação sobre versionamento

Existem duas numerações distintas no projeto, que não devem ser confundidas:

- **Versão de produto** (V5.1.9): marca entregas visuais/funcionais de frontend.
- **Versão técnica do backend** (`0.2.0`): versão do pacote Python da API.

Nenhuma das duas foi alterada por `PEDROCORE-REPLAN-01` (01A a 01E).

## Próximos passos técnicos

- QA Intelligence real (parser de relatório, classificador de risco) para preencher o skeleton com achados reais (ainda não implementada).
- Artifact Reader real (leitura automática de arquivo) e suporte a artefatos visuais (ainda não implementados).
- Orchestration module e/ou endpoint `/api/orchestrate` — avaliados e adiados na etapa `01I`.
- Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`, seção 12, para o escopo completo de `PEDROCORE-IMPLEMENT-01`.
