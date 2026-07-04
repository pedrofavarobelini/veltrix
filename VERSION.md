# PedroCore IA — Versionamento

Atualizado em: 04/07/2026

## Versão atual de produto

V5.1.9

## Versão técnica do backend

0.2.0 (`apps/api/pyproject.toml`) — sem alteração nesta frente.

## Frente atual

PEDROCORE-IMPLEMENT-01A/01B — Task Router mínimo + metadados de resposta.

## Status atual

`PEDROCORE-REPLAN-01` (01A a 01E) concluída no escopo documental (commits `1e5a8cb`, `6e7badd`, `c1e7816`, `8c68b67`, `cc808a7`). Primeira implementação de código pós-reformulação: Task Router mínimo integrado a `POST /api/chat`, com metadados de tarefa no `ChatResponse` e warnings de fallback crítico. Testes backend passando (15/15). Sem alterações de frontend, design, providers reais ou `.env`.

## Observação sobre versionamento

Existem duas numerações distintas no projeto, que não devem ser confundidas:

- **Versão de produto** (V5.1.9): marca entregas visuais/funcionais de frontend.
- **Versão técnica do backend** (`0.2.0`): versão do pacote Python da API.

Nenhuma das duas foi alterada por `PEDROCORE-REPLAN-01` (01A a 01E).

## Próximos passos técnicos

- Prompt Builder real consumindo `task_type`/`context`/`metadata` (ainda não implementado).
- Project Context real por sistema externo (ainda não implementado).
- Audit/logs básico (ainda não implementado).
- Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`, seção 12, para o escopo completo de `PEDROCORE-IMPLEMENT-01`.
