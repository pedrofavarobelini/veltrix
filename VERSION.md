# PedroCore IA — Versionamento

Atualizado em: 05/07/2026

## Versão atual de produto

V5.1.9

## Versão técnica do backend

0.2.0 (`apps/api/pyproject.toml`) — sem alteração nesta frente.

## Frente atual

PEDROCORE-IMPLEMENT-03 — MVP backend (Blocos 1–7): QA textual real, release gate conservador, `/api/orchestrate`, safe mode.

## Status atual

`PEDROCORE-REPLAN-01` (01A a 01E) concluída no escopo documental. `PEDROCORE-IMPLEMENT-01A/01B` commitada em `577bc88`; `01C–01H` commitada em `95cbfab`; `PEDROCORE-IMPLEMENT-02` commitada em `e115672`. Nesta etapa (`IMPLEMENT-03`, ainda sem commit): QA textual real por heurística local determinística, release gate conservador com `blocked_reason`, endpoint `POST /api/orchestrate` (pipeline centralizado, também usado por `/api/chat`), safe mode com `allow_real_provider=false` por padrão, autenticação interna opcional para `/api/orchestrate`, contrato padronizado de warnings/errors e audit não persistente completo. Testes backend passando (`125 passed, 2 warnings`). Sem alterações de frontend, design, providers reais ou `.env`.

## Observação sobre versionamento

Existem duas numerações distintas no projeto, que não devem ser confundidas:

- **Versão de produto** (V5.1.9): marca entregas visuais/funcionais de frontend.
- **Versão técnica do backend** (`0.2.0`): versão do pacote Python da API.

Nenhuma das duas foi alterada por `PEDROCORE-REPLAN-01` (01A a 01E).

## Próximos passos técnicos

- Validar, documentar em definitivo e commitar `PEDROCORE-IMPLEMENT-03` (MVP backend Blocos 1–7).
- Testes finais globais e documentação final do MVP antes de qualquer tag.
- Artifact Reader real (leitura automática de arquivo) e análise visual real continuam não implementados, por decisão.
- Provider real em fluxo crítico somente com autorização explícita (`allow_real_provider=true`) e revisão específica.
