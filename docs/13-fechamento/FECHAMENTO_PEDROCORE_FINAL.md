# Fechamento final — PedroCore IA (core operacional seguro, local)

## 1. Estado final

O PedroCore IA está finalizado localmente como **core operacional seguro**: API de orquestração de IA com QA textual local determinístico, release gate conservador, policy enforcement forte, integrações reais controladas por flags (todas desabilitadas por padrão) e audit não persistente. Tag final local: `v7.0.0`.

## 2. Escopo final implementado

Backend FastAPI (`apps/api`) com módulos: `task_router`, `project_context`, `policy_enforcement`, `prompt_builder`, `artifacts`, `artifact_reader`, `qa_analysis`, `qa_response`, `visual_qa`, `ocr`, `exploration` (+ `playwright_adapter`), `orchestration`, `contracts`, `audit`, `real_features`, `providers`, `chat`. Frontend React (V5.1.9) preservado, com autorização explícita de provider real por sessão.

## 3. MVP backend (Blocos 1–7, tag v6.0.0 em `ee2ac68`)

QA textual heurístico local, release gate conservador, `/api/orchestrate`, safe mode (`allow_real_provider=false` default), auth interna opcional, warning/error contract com severidades, audit não persistente.

## 4. IMPLEMENT-04 (Blocos 8–11, `18d1fc5`)

Contrato FinGuard fake (`finguard`/`finguard-local` read-only), Artifact Reader allowlisted default-off, QA visual stub com revisão humana, agente exploratório assistido (`can_execute_actions=false`).

## 5. IMPLEMENT-05 (`33a7dc2`…`3bcfa05`)

Flags/guards centrais (`real_features`), testes opt-in skipados, policy enforcement forte, reader consolidado, OCR local opt-in (dependência não instalada → bloqueio seguro), guard multimodal (contrato-somente), Playwright read-only opt-in (ações interativas sempre bloqueadas).

## 6. FINALIZE-06 (`e08c519` + commit documental)

Somente `local_qa` aprova release gate; provider real exige revisão humana; documentação final e tag `v7.0.0`.

## 7. Habilitado por padrão

`/api/chat` (sem API key), `/api/orchestrate` (modo dev/local com warning se chave interna ausente), providers `mock` e `local_qa`, QA textual local, release gate conservador, policy enforcement (`PEDROCORE_ENFORCE_PROJECT_POLICY=true`), exigência de revisão humana para recursos reais (`...REQUIRE_HUMAN_REVIEW...=true`), audit não persistente, safe mode.

## 8. Desabilitado por padrão

Providers reais (Gemini/OpenAI/Claude/DeepSeek/Grok — exigem `allow_real_provider=true` por request), Artifact Reader, OCR, QA visual multimodal, Playwright, testes reais opt-in (6 flags `PEDROCORE_RUN_REAL_*_TESTS`), auth interna (`PEDROCORE_INTERNAL_API_KEY` vazia = modo dev).

## 9. `/api/chat`

`POST /api/chat` com `{message, mode, provider, ...}` — contrato legado 100% preservado, sem API key. Campos novos sempre com default seguro.

## 10. `/api/orchestrate`

`POST /api/orchestrate` com o mesmo schema + resposta estruturada completa (`qa`, `release_gate`, `visual_qa_analysis`, `exploration`, `audit`, `warnings` com severidade, `warning_codes`, `blocked_reason`, `status`). Exemplos: `docs/10-api/EXEMPLOS_API_MVP.md`.

## 11. Como o FinGuard chamará o PedroCore (futuro)

Cliente HTTP no repositório do FinGuard (frente separada) enviando payloads do contrato (`docs/11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO.md`) para `POST /api/orchestrate` com header `X-PedroCore-Api-Key`, tratando `blocked_reason`/`release_gate`/`warning_codes`.

## 12. Testes padrão

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -q
```
Resultado final: `216 passed, 6 skipped, 2 warnings` (skipped = opt-in; warnings = deprecações conhecidas Starlette/Pydantic).

## 13. Testes opt-in

Definir a flag correspondente (`PEDROCORE_RUN_REAL_INTEGRATION_TESTS`, `..._FINGUARD_...`, `..._PROVIDER_...`, `..._OCR_...`, `..._MULTIMODAL_...`, `..._PLAYWRIGHT_...`) como `true` no ambiente do processo e rodar `pytest tests/test_real_optin.py`. Exigem configuração real (chaves/dependências) e geram efeitos reais — uso consciente.

## 14. Artifact Reader

`PEDROCORE_ARTIFACT_READER_ENABLED=true` + `PEDROCORE_ARTIFACT_ALLOWED_DIRS` (allowlist) + limites/extensões. Nunca lê `.env`, binário, segredo, traversal ou caminhos FinGuard; nunca escreve/deleta/executa.

## 15. OCR

`PEDROCORE_OCR_ENABLED=true` + instalar `pytesseract`/`PIL` manualmente (aprovação explícita). Engine local apenas; texto sanitizado; sempre revisão humana.

## 16. QA visual multimodal

`PEDROCORE_MULTIMODAL_PROVIDER_ENABLED=true` + `PEDROCORE_VISUAL_QA_ENABLED=true` + `allow_real_provider=true`. Nesta versão, mesmo com tudo ligado, o envio real não é executado (contrato preparado; frente futura).

## 17. Playwright read-only

`PEDROCORE_EXPLORATION_PLAYWRIGHT_ENABLED=true` + allowlist `PEDROCORE_EXPLORATION_ALLOWED_BASE_URLS` + instalar Playwright manualmente. Navegação somente leitura; clique/digitação/submissão/login sempre bloqueados.

## 18. Autorização de provider real

Por request: `allow_real_provider=true` no payload (o frontend possui autorização explícita por sessão). Sem isso: `PROVIDER_REAL_BLOCKED` + fallback Mock. Provider real nunca aprova release gate sozinho.

## 19. Como o release gate decide

Aprova (`can_advance=true`) somente com: análise textual local (`local_qa`) sobre artefatos textuais com sucesso explícito, sem falha/erro, risco `low`, confiança ≥ 0.6, sem fallback, sem safe-mode block, sem truncamento, sem path rejeitado. Bloqueia com `blocked_reason` em todos os demais casos (mock, provider real, visual-only, OCR-only, exploração-only, evidência insuficiente).

## 20. Garantias de segurança

Sem execução de comandos (por payload ou autônoma); sem escrita/deleção de arquivos fora do escopo do repositório do próprio PedroCore em frentes autorizadas; leitura de disco somente pelo reader allowlisted; segredos nunca ecoados em resposta/audit/logs; audit sem conteúdo de artefatos; FinGuard intocado; `.env`/`apps/api/.env`/`apps/web` intocados nesta frente; nenhum push.

## 21. Limitações finais

QA textual é heurístico (não substitui revisão humana); QA visual não interpreta imagens; multimodal é contrato-somente; OCR/Playwright dependem de instalação manual; detecção de segredos por padrões (possíveis falsos negativos); histórico de chat só no navegador; audit não persistente.

## 22. Riscos conhecidos

`GEMINI_API_KEY` preenchida no `.env` real (chamada real possível com autorização explícita); fallback Mock pode mascarar falha de provider se `fallback_used` for ignorado; documentação legada duplicada em `docs/` ainda não saneada.

## 23. Rollback

Cada subfrente é um commit isolado; rollback = `git revert <hash>` (nunca `reset`/`rebase`). Tags `v6.0.0` (MVP) e `v7.0.0` (fechamento) marcam estados estáveis. Flags de ambiente permitem desligar qualquer recurso real sem código.

## 24. Próximos passos opcionais

Cliente HTTP no repositório FinGuard; push para GitHub/portfólio; deploy; execução real de OCR/Playwright/multimodal com aprovação; logs persistentes/dashboard somente se decisão de produto mudar; saneamento de docs legadas.

## 25. Bloco 12

**Cancelado por decisão de produto** (Decisão 060). Não é pendência.

## 26. FinGuard

**Nenhuma alteração foi feita no FinGuard** em nenhuma frente: nenhum arquivo lido, nenhum comando executado, nenhum commit, nenhuma integração executando lá.

## 27. Push

**Nenhum push foi feito.** Todo o trabalho é local; publicação é decisão humana futura.
