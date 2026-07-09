# PedroCore IA — Versionamento

Atualizado em: 09/07/2026

## Versão atual de produto

V5.1.9

## Versão técnica do backend

0.2.0 (`apps/api/pyproject.toml`) — sem alteração nesta frente.

## Frente atual

Projeto **finalizado localmente**: `PEDROCORE-IMPLEMENT-05` (05A–05F, integrações reais controladas) e `PEDROCORE-FINALIZE-06` (06A enforcement final + 06B fechamento) concluídas. Tag final local: `v7.0.0`. Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md`.

DOCFIX anterior: saneamento documental/Obsidian, sem alteração de código de produção, testes, tags, merge ou push. Mapeamento central: `docs/00_MAPEAMENTO_GERAL_PEDROCORE.md`.

Frente anterior: `PEDROCORE-MODEL-FOUNDATION-01` — fundação de inteligência própria, commitada em `689e50a`. Testes na época: `257 passed, 6 skipped, 2 warnings`. Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01.md`.

Frente commitada mais recente: `PEDROCORE-QA-SAFETY-HARDENING-01` — endurecimento de QA/safety sem reabrir o core funcional, commitada em `d6106b7`. Pytest: `341 passed, 6 skipped, 2 warnings`. Eval harness: `14/14 passed`, `risk_level="none"`. Sem provider real, sem rede real em testes, sem treinamento/fine-tuning, sem tocar FinGuard ou `qa:finalize:02`. Ver `docs/16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01.md`.

Frente documental atual: `PEDROCORE-DOCS-GRAPH-LINKING-01` — linkagem Markdown/Obsidian em documentacao, sem alteracao de codigo, testes, `.env`, provider real, `local_model` real, FinGuard, push, tag ou merge.

## Status atual

`PEDROCORE-REPLAN-01` (01A a 01E) concluída no escopo documental. `PEDROCORE-IMPLEMENT-01A/01B` commitada em `577bc88`; `01C–01H` commitada em `95cbfab`; `PEDROCORE-IMPLEMENT-02` commitada em `e115672`. `PEDROCORE-IMPLEMENT-03` (MVP backend Blocos 1–7) commitada em `6ed4c41`: QA textual real por heurística local determinística, release gate conservador com `blocked_reason`, endpoint `POST /api/orchestrate` (pipeline centralizado, também usado por `/api/chat`), safe mode com `allow_real_provider=false` por padrão, autenticação interna opcional para `/api/orchestrate`, contrato padronizado de warnings/errors e audit não persistente completo. `PEDROCORE-FINALIZE-04` foi consolidada em `ee2ac68`, commit para o qual aponta a tag anotada `v6.0.0` com a mensagem `v6.0.0 - MVP backend PedroCore IA`. Testes backend passando (`125 passed, 2 warnings`). Sem alterações de frontend, design, providers reais ou `.env`.

## Tags atuais

`v7.0.0` é a tag final local do core operacional seguro e aponta para `33b2c0489c19776ef460fc85dea3c24298b46a3c`.

`v6.0.0` existe e aponta para `ee2ac68679feea6ac108abba8726d11da101576c` (`ee2ac68`). A tag representa o fechamento do MVP backend; ela não é a tag final local atual.

Resumo:

- `v6.0.0` = MVP backend.
- `v7.0.0` = fechamento técnico local do core operacional seguro.
- `d6106b7` = `PEDROCORE-QA-SAFETY-HARDENING-01`, hardening QA/safety posterior ao fechamento local.
- Pendência obrigatória de código/teste/Git = zero no estado final registrado.
- Pendência documental obrigatória = tratada por este DOCFIX, se o diff for aceito.

## Observação sobre versionamento

Existem duas numerações distintas no projeto, que não devem ser confundidas:

- **Versão de produto** (V5.1.9): marca entregas visuais/funcionais de frontend.
- **Versão técnica do backend** (`0.2.0`): versão do pacote Python da API.

Nenhuma das duas foi alterada por `PEDROCORE-REPLAN-01` (01A a 01E).

## Próximos passos (opcionais, pós-fechamento)

- Cliente HTTP no repositório do FinGuard (frente separada, com aprovação própria).
- Push para GitHub/portfólio e deploy — decisões humanas futuras.
- Execução real de OCR/multimodal/Playwright somente com flags, dependências instaladas manualmente e revisão humana.
- Saneamento adicional de documentos históricos duplicados, se o usuário quiser reduzir ruído do vault.
- Bloco 12 (dashboard/logs/admin): cancelado por decisão de produto — não é pendência.
