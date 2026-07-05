# PedroCore IA — Versionamento

Atualizado em: 05/07/2026

## Versão atual de produto

V5.1.9

## Versão técnica do backend

0.2.0 (`apps/api/pyproject.toml`) — sem alteração nesta frente.

## Frente atual

PEDROCORE-IMPLEMENT-04 — Expansão operacional segura (Blocos 8–11): contrato FinGuard fake, Artifact Reader allowlisted, QA visual stub e agente exploratório assistido.

## Status atual

`PEDROCORE-REPLAN-01` (01A a 01E) concluída no escopo documental. `PEDROCORE-IMPLEMENT-01A/01B` commitada em `577bc88`; `01C–01H` commitada em `95cbfab`; `PEDROCORE-IMPLEMENT-02` commitada em `e115672`. `PEDROCORE-IMPLEMENT-03` (MVP backend Blocos 1–7) commitada em `6ed4c41`: QA textual real por heurística local determinística, release gate conservador com `blocked_reason`, endpoint `POST /api/orchestrate` (pipeline centralizado, também usado por `/api/chat`), safe mode com `allow_real_provider=false` por padrão, autenticação interna opcional para `/api/orchestrate`, contrato padronizado de warnings/errors e audit não persistente completo. `PEDROCORE-FINALIZE-04` foi consolidada em `ee2ac68`, commit para o qual aponta a tag anotada `v6.0.0` com a mensagem `v6.0.0 - MVP backend PedroCore IA`. Testes backend passando (`125 passed, 2 warnings`). Sem alterações de frontend, design, providers reais ou `.env`.

## Tag atual

`v6.0.0` existe e aponta para `ee2ac68679feea6ac108abba8726d11da101576c` (`ee2ac68`). A tag representa o fechamento do MVP backend; ela não inclui Artifact Reader real, QA visual, integração real com FinGuard, dashboard, log persistente, Blocos 7–11 do planejamento maior, Bloco 12 ou Blocos 13–15 finais.

## Observação sobre versionamento

Existem duas numerações distintas no projeto, que não devem ser confundidas:

- **Versão de produto** (V5.1.9): marca entregas visuais/funcionais de frontend.
- **Versão técnica do backend** (`0.2.0`): versão do pacote Python da API.

Nenhuma das duas foi alterada por `PEDROCORE-REPLAN-01` (01A a 01E).

## Próximos passos técnicos

- Bloco 13 — Documentação final; Bloco 14 — Testes finais completos; Bloco 15 — Fechamento Git/tag futuro.
- Integração real no repositório FinGuard (cliente HTTP) em frente separada.
- OCR real, QA visual real com provider multimodal e Playwright real em frentes futuras.
- Provider real em fluxo crítico somente com autorização explícita (`allow_real_provider=true`) e revisão específica.
- Bloco 12 (dashboard/logs/admin): cancelado por decisão de produto — não é pendência.
