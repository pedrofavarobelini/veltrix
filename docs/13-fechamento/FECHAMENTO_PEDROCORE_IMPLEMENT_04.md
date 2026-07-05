# Fechamento — PEDROCORE-IMPLEMENT-04 — Expansão operacional segura (Blocos 8–11)

## 1. Escopo dos Blocos 8 a 11

- **Bloco 8** — Contrato seguro FinGuard → PedroCore com payload fake (sem tocar no repositório real do FinGuard).
- **Bloco 9** — Artifact Reader real controlado por allowlist, desabilitado por padrão, sem uso em FinGuard real.
- **Bloco 10** — QA visual/exploratório inicial seguro (stub), sem OCR real e sem IA visual real.
- **Bloco 11** — Agente exploratório assistido, modo plano/manual, sem Playwright real.

## 2. O que foi implementado

- **Bloco 8:** `origin_system` `finguard` e `finguard-local` com Project Context read-only e `allowed_tasks` próprios (QA + exploração); contrato completo em `docs/11-integracoes/CONTRATO_FINGUARD_PEDROCORE.md`; payloads fake testados em `tests/test_finguard_contract.py`; Artifact Reader indisponível para origem FinGuard (duas camadas de bloqueio).
- **Bloco 9:** módulo `apps/api/app/modules/artifact_reader/` com `ArtifactReaderService.read()` — habilitação por `PEDROCORE_ARTIFACT_READER_ENABLED` (default `false`), allowlist `PEDROCORE_ARTIFACT_ALLOWED_DIRS`, extensões `.txt,.md,.log,.json,.csv`, limites 20k/100k; integração via `OrchestrationService._apply_artifact_reader` (arquivo lido vira artefato textual, `ARTIFACT_READER_USED`); 10 novos warning codes; variáveis adicionadas ao `.env.example` sem valor real.
- **Bloco 10:** módulo `apps/api/app/modules/visual_qa/` gerando `visual_qa_analysis` conservador para `screenshot`/`image`/`pdf`/`playwright_trace` (`not_analyzed`, `stub`, `requires_human_review=true`, `can_advance=false`, `ocr_attempted=false`, `provider_attempted=false`, `playwright_attempted=false`); release gate nunca avança apenas com visual (`VISUAL_QA_BLOCKED_FOR_RELEASE_GATE`); 4 novos codes.
- **Bloco 11:** módulo `apps/api/app/modules/exploration/` gerando `exploration` determinístico (plano, passos manuais a partir de `context.routes`, riscos por keyword, evidências exigidas, confirmações humanas, ações bloqueadas) para as 3 novas tasks do Task Router; `can_execute_actions=false` sempre; pedidos destrutivos geram `EXPLORATION_ACTION_BLOCKED`; 6 novos codes.

## 3. O que foi deliberadamente bloqueado

- Leitura de qualquer caminho contendo "finguard" (reader) e uso do reader por origem FinGuard (orquestração).
- Leitura de `.env`, binários, segredos identificáveis, path traversal, extensões fora da lista e arquivos acima do limite.
- OCR, provider multimodal e Playwright no QA visual (flags explícitas de não-tentativa).
- Qualquer execução de ação pelo agente exploratório (navegador, clique, comando, escrita, deleção).
- Release gate por evidência visual não analisada ou por plano exploratório isolado.
- Provider real sem `allow_real_provider=true` (safe mode inalterado).

## 4. Bloco 12

**Cancelado por decisão de produto** (Decisão 060). Dashboard/logs/admin não serão implementados e não constam como pendência.

## 5–6. Arquivos e mapa de alterações

Criados: `artifact_reader/` (3), `visual_qa/` (3), `exploration/` (3), `tests/test_finguard_contract.py`, `tests/test_artifact_reader.py`, `tests/test_visual_qa.py`, `tests/test_exploration.py`, `docs/11-integracoes/CONTRATO_FINGUARD_PEDROCORE.md`, este fechamento.

Alterados: `contracts/codes.py` (20 códigos novos + severidades), `task_router/service.py` (3 strategies), `project_context/service.py` (finguard-local + tasks + notas), `orchestration/schemas.py` e `service.py` (reader/visual/exploration no pipeline), `orchestration/router.py` (2 campos novos), `tests/test_project_context.py`, `apps/api/.env.example`, `README.md`, `VERSION.md`, `docs/03-versoes/ROADMAP.md`, `docs/08_CHANGELOG.md`, `docs/09_STATUS_ATUAL.md`, `docs/07-decisoes/DECISOES_TECNICAS.md` (056–060), `docs/10-api/EXEMPLOS_API_MVP.md`.

O mapa detalhado por arquivo (linhas +/-) está no relatório da frente e no `git show` do commit.

## 7. Testes executados

- `compileall app tests -q` — sem erros.
- `pytest -q` — `166 passed, 2 warnings` (125 anteriores + 41 novos; warnings pré-existentes Starlette/Pydantic).
- Testes de reader usam exclusivamente `tmp_path`; nenhum teste chama provider real, faz request externo, executa OCR ou Playwright.

## 8. Garantias de segurança

`apps/web`, `.env` e `apps/api/.env` intocados; FinGuard real não acessado (nenhum arquivo lido, nenhum comando executado); provider real não chamado em teste; reader desabilitado por padrão e restrito por allowlist; path traversal/`.env`/binário/segredo bloqueados; visual QA sem OCR/multimodal/Playwright; agente exploratório sem ações autônomas; release gate conservador inalterado; tag `v6.0.0` intocada em `ee2ac68`; sem push.

## 9. Limitações

- O reader não foi apontado para nenhum diretório real — allowlist vazia por padrão.
- A análise visual não interpreta conteúdo de imagem; apenas registra e exige revisão humana.
- O plano exploratório é heurístico e genérico; não substitui um roteiro de QA especializado.
- O contrato FinGuard só está exercitado com payloads fake.

## 10. Próximos passos

- Bloco 13 — Documentação final.
- Bloco 14 — Testes finais completos.
- Bloco 15 — Fechamento Git/tag futuro.
- Integração real no repositório FinGuard (cliente HTTP) em frente separada.
- OCR real em frente futura.
- QA visual real com provider multimodal em frente futura.
- Playwright real em frente futura.
