# PedroCore IA — Changelog

## PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION — Etapa 1: catálogo de providers

Status: **implementado, passivo e sem alteração de roteamento**.

- Novo módulo `provider_catalog` (`schemas.py` + `service.py`): caracterização tipada de `gemini`, `claude`, `openai`, `deepseek`, `grok`, `mock`, `local_qa` e `local_model`, com adapter, categoria, modelos conhecidos, capacidades, tasks compatíveis e prioridade estática.
- Estados **separados** e nunca inferidos entre si: `registered`, `implemented`, `configured`, `homologation`, `authorized_for_auto`, `availability`, `health`. Ter chave não homologa, não autoriza e não torna saudável.
- Invariantes recusam combinações incoerentes (não implementado configurado/homologado/elegível; `healthy` sem evidência; `healthy` em provider real sem avaliação real; `required_config_keys` com valor em vez de nome de env var).
- Catálogo é **consultivo**: o pipeline continua usando `AUTO_REAL_PROVIDER_CANDIDATES = ("gemini",)`. Nenhuma chamada real, nenhum fallback entre providers reais, contrato público intacto.
- Testes: `tests/test_provider_catalog.py` e `tests/test_provider_auto_characterization.py`. Ver [[17-multi-provider-safe-evolution/ETAPA_1_CATALOGO_PROVIDERS]].

## PEDROCORE-OBSERVABILIDADE-LOCAL-01 — 2026-07-18

Status: **implementado e validado localmente**.

- Ring buffer sanitizado, limitado e default-off; habilitação somente local/QA/test, bloqueio em produção e acesso HTTP por loopback.
- Pipeline real instrumentado com provider solicitado/selecionado/efetivo, tentativas, timeout, fallback, timeline, resposta pública, QA, release gate, avaliação, sinais, memória e audit ID.
- Painel técnico em `#/observability` com lista, filtros, detalhe e smoke Gemini; nenhuma UI técnica adicionada ao FinGuard.
- Smoke Gemini protegido por duplo opt-in, confirmações de rede/custo/chave e payload sintético imutável; nesta execução houve 0 chamadas reais porque as flags estavam desligadas.
- Replay local FinGuard → PedroCore → FinGuard aprovado em sucesso, relatório/memória, fallback e falha total, com cleanup.
- Pytest integral: `368 passed, 7 skipped, 2 warnings`; frontend build exit 0.
- Commits: `b22338a`, `df6d72f`, `f995d5e`, `3b11b36`. Ver [[13-fechamento/FECHAMENTO_PEDROCORE_OBSERVABILIDADE_LOCAL_01]].

## FINGUARD-PEDROCORE-ASSISTANT-REAL-PROVIDER-QA-01 - Fechamento: fallback seguro + validacao real com Gemini

Status: **validado localmente com Gemini real** (`provider=auto`, `allow_real_provider=true`), sem push/tag/merge, sem alterar `.env`/chave, sem rodar Gemini real na suite padrao.

### Correcao de fallback (bug encontrado no uso visual do Assistente FinGuard)

- **Bug**: `_mock_fallback()` (`orchestration/service.py`) montava a resposta de fallback chamando `MockProvider` em modo `"tecnico"` (modo default de `ChatRequest` quando o chamador nao envia `mode`, caso do FinGuard) e embutia o erro tecnico bruto na propria resposta conversacional — a `answer` chegava ao usuario final com texto como "Resposta tecnica simulada do MockProvider", "mock-v1", "Modelo solicitado", "A V2 possui arquitetura multi-provider" e ate o traceback resumido do provider real (`Falha no GeminiProvider: 503 UNAVAILABLE...`).
- **Correcao**: `_mock_fallback()` agora retorna sempre uma resposta segura e conservadora fixa (`SAFE_FALLBACK_ANSWER`), sem citar provider, modelo, classe de excecao ou erro tecnico bruto. Detalhe tecnico continua disponivel apenas em `error`/`error_code`/`warning_codes`/`audit` (nunca expostos em `answer`; o proprio schema publico `OrchestrateResponse` ja nao expunha `error` bruto, so `error_code`).
- **Testes atualizados/criados** em `tests/test_provider_real_safety.py`: 2 asserts que dependiam do texto tecnico antigo foram corrigidos para verificar ausencia do texto no lugar de presenca; 2 testes novos (`test_fallback_answer_never_leaks_technical_debug_text`, `test_fallback_answer_never_leaks_technical_debug_text_for_auto_real_provider`) cobrem os 3 gatilhos de fallback (provider invalido, provider real bloqueado por safe mode, `auto` sem provider real disponivel) contra uma lista fixa de substrings tecnicas proibidas.
- **Eval harness** (`app/modules/eval_harness/fixtures.py`): caso `invalid-provider-falls-back-safely` atualizado para exigir o novo texto seguro e proibir explicitamente `mockprovider`, `mock-v1`, `modelo solicitado`, `erro técnico`, `fallback acionado`, `provider_inexistente`.
- Suite padrao apos a correcao: **351 passed, 7 skipped** (era 341 passed, 6 skipped antes desta correcao — 2 testes hardening novos + 1 skip novo por causa do proprio marker `expected_guarded_call`; nenhum teste removido).

### Validacao manual com Gemini real (2026-07-09)

- PedroCore local subido com `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3333` (nunca `python -m uvicorn` generico) e `GEMINI_API_KEY` carregada só via `.env` local (nunca impressa, nunca exportada manualmente).
- Primeira chamada real `provider=auto` + `allow_real_provider=true` retornou fallback: o modelo padrao configurado (`GEMINI_MODEL=gemini-3.5-flash`, em `.env`) respondeu **503 UNAVAILABLE ("high demand")** — indisponibilidade transitoria do lado do Google, confirmada via diagnostico direto do `GeminiProvider` (chave valida, `is_configured=True`).
- Diagnostico adicional (fora da suite, script descartavel) testou outros modelos Gemini: `gemini-2.5-flash` respondeu com sucesso; `gemini-2.0-flash` retornou 429 (quota); `gemini-flash-latest` tambem 503. Isso confirma que a integracao real (chave, roteamento, política de autorizacao) funciona corretamente — a indisponibilidade e especifica do modelo `gemini-3.5-flash` no momento do teste, nao um bug do PedroCore.
- Com `GEMINI_MODEL=gemini-2.5-flash` sobreposto **apenas via variavel de ambiente do processo** (sem alterar `.env`), a mesma chamada `provider=auto`/`allow_real_provider=true` retornou `provider_used="gemini"`, `model="gemini-2.5-flash"`, `fallback_used=false`, resposta conversacional completa (plano de quitacao de divida considerando renda/aluguel/alimentacao) e disclaimer financeiro presente. Nenhuma configuracao permanente foi alterada; `GEMINI_MODEL=gemini-3.5-flash` continua o default em `.env`.
- Confirmado: `GEMINI_API_KEY` nunca impressa, nunca commitada, nunca exposta em log/resposta/teste.

### Comportamento (sem mudanca desde a implementacao original)

- `POST /api/orchestrate` aceita `provider=auto` como politica controlada; sem `allow_real_provider=true`, cai em mock seguro.
- Com `allow_real_provider=true`, `provider=auto` escolhe Gemini quando `GEMINI_API_KEY` esta configurada no ambiente PedroCore; `provider=gemini` continua exigindo autorizacao explicita.
- Se houver autorizacao mas nenhum provider real configurado, retorna fallback Mock com `PROVIDER_REAL_UNAVAILABLE`.
- `local_qa` permanece intacto para QA/release gate; mock segue default seguro.
- Testes padrao usam Gemini stubado/mocado e o guard estrutural continua bloqueando rede real. Teste real Gemini fica opt-in via `PEDROCORE_RUN_REAL_GEMINI_TESTS=true`, skipado por padrao.

Atualizado em: 09/07/2026

## PEDROCORE-DOCS-GRAPH-LINKING-01 — Linkagem Obsidian e integracao QA Safety

Status: documentacao atualizada nesta tarefa, sem alteracao de codigo, testes, `.env`, FinGuard, provider real, `local_model` real, push, tag, merge ou commit.

### Motivo

Integrar ao grafo Obsidian a frente `PEDROCORE-QA-SAFETY-HARDENING-01`, commitada em `d6106b7`, reduzindo notas soltas e conectando `docs/16-qa-safety-hardening/` aos MOCs principais.

### Atualizado

- MOCs centrais: `MOC_PEDROCORE_IA`, `MOC_QA_RELEASE_GATE`, `MOC_TESTES`, `MOC_SEGURANCA`, `MOC_VERSOES_STATUS`.
- MOCs novos aprovados: `MOC_QA_SAFETY_HARDENING` e `MOC_ESTUDO_PEDROCORE`.
- Mapeamento/status/roadmap atualizados para registrar `d6106b7`, pytest `341 passed, 6 skipped, 2 warnings` e eval harness `14/14 passed`, `risk_level="none"`.
- `docs/16-qa-safety-hardening/` conectado ao mapa geral, QA/release gate, seguranca, testes e status.
- `docs/15-estudo-pedrocore/` recebeu links de retorno minimos para MOCs e fontes tecnicas.

### Confirmacoes tecnicas preservadas

- PedroCore IA continua sendo orquestrador central, nao modelo treinado.
- Sem fine-tuning, autoaprendizado ou RAG real.
- Report Memory permanece default-off e nao e treinamento.
- `local_model` real segue fora de escopo; provider real continua bloqueado por padrao.
- Provider real e rede real nao foram chamados em testes da frente `d6106b7`.
- FinGuard e `qa:finalize:02` ficaram intocados.

## PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01 — Inteligência de ecossistema (pacote A+B+C+D)

Status: implementada, validada e commitada em `e0ff8e3`. Base: `689e50a`.

### Fase A — Ecosystem finalize

- `ChatRequest` + `allow_local_model=false` e `context_from_memory=false` (aditivos, default seguro).
- 7 task types novos (`assistant_chat`, `ecosystem_assistant`, `finance_advice`, `project_status`, `report_memory_query`, `local_model_chat`, `evaluation_run`); FinGuard recebeu somente `assistant_chat`/`finance_advice`/`project_status`/`report_memory_query` como consumidor read-only.
- `finance_advice` conservador: disclaimer obrigatório anexado à resposta + `FINANCIAL_DISCLAIMER`.
- Intelligence Layer conectada: `plan.instructions` → seção `[Plano de inteligência]` do prompt (Prompt Builder com campos opcionais retrocompatíveis).
- `AssistantResponsePayload` + `build_assistant_payload()`; `OrchestrateResponse.memory_used` (aditivo).
- Contrato: `docs/10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT.md`.

### Fase B — Report Memory

- Módulo `report_memory/` (entry/query/snapshot; repositórios in-memory e `local_json` opcional; segredos redigidos com `[REDACTED]`).
- Flag `PEDROCORE_REPORT_MEMORY_PERSISTENCE=off` (default) | `memory` | `local_json` (+ `PEDROCORE_REPORT_MEMORY_DIR`).
- Rotas novas com auth interna opcional: `POST /api/reports/analyze`, `POST /api/reports/ingest`, `GET /api/project-memory/{project_id}/summary`.
- `/api/orchestrate` com `context_from_memory=true` anexa snapshot limitado (2k chars, `[Memória técnica]`) e marca `memory_used=true`; codes `REPORT_MEMORY_USED/DISABLED/EMPTY/IS_NOT_TRAINING`.
- Contrato: `docs/10-contratos/CONTRATO_REPORT_MEMORY.md`. **Relatórios não treinam IA.**

### Fase C — Local Model Provider opt-in

- `providers/local_model_provider.py`: `local_model` registrado no registry (default OFF, `real_provider=false`, `configured=false` sem flag); gate cumulativo (`allow_local_model` + `PEDROCORE_ENABLE_LOCAL_MODEL` + backend + task não crítica); codes `LOCAL_MODEL_*`; fora de `RELEASE_GATE_TRUSTED_PROVIDERS`.
- **Sem rede nesta frente**: transport padrão None (fallback controlado); testes com fake transport; flags novas apenas em `.env.example`.

### Fase D — Eval Harness

- Módulo `eval_harness/` com `EvalCase` (rejeita `allow_real_provider=true`), `EvalRunResult`, 11 fixtures determinísticas e executor `uv run python -m app.modules.eval_harness.run` (verificado: 11/11, exit 0). Não é benchmark de LLM; sem provider real, sem internet.

### Testes

- Novos: `test_ecosystem_contract.py`, `test_report_memory.py`, `test_local_model_provider.py`, `test_eval_harness.py` (39 testes).
- Atualizados: `test_local_model_contract.py` (local_model agora registrado porém disabled) e `test_project_context.py` (allowed_tasks exatos do FinGuard). Suíte: **`296 passed, 6 skipped, 2 warnings`**.

### Não alterado / não feito

- Sem provider real, sem `allow_real_provider=true`, sem `.env`, sem FinGuard, sem treinamento/fine-tuning/LoRA/autoaprendizado, sem backend instalado, sem modelo baixado, sem rede em teste, sem push/tag/merge.

## PEDROCORE-MODEL-FOUNDATION-01 — Fundação de inteligência própria

Status: implementada, validada e commitada em `689e50a`.

### Implementado

- **Intelligence Layer** (`apps/api/app/modules/intelligence_layer/`): `IntelligenceContextPolicy` (validação rejeita `allow_real_provider=true`), `IntelligencePlan` (task_type, response_profile, safety_flags, instructions, memory_hints, evaluation_hints) e `IntelligenceLayerService.build_plan()` determinístico. Integração retrocompatível: `OrchestrationService` calcula o plano após policy e o anexa a `OrchestrationOutcome.intelligence_plan` como metadado **interno** — não exposto em `ChatResponse`/`OrchestrateResponse`.
- **Report Intelligence Foundation** (`apps/api/app/modules/report_intelligence/`): `TechnicalReportInput`/`ReportSignal`/`ReportMemorySummary` e serviço determinístico (`normalize_report`, `extract_signals`, `summarize_memory`), sem persistência, sem embeddings/RAG, sem rota nova. Relatórios não treinam IA — geram sinais explicáveis com severidade (`provider_real_used`/`database_safety_risk` = `critical`; `provider_real_blocked` = `info`; `QA_RISK_CRITICAL` não invalida suíte passed).
- **Local Model Provider Contract** (`apps/api/app/modules/providers/local_model_contract.py`): contrato futuro do provider generativo local (`local_model` ≠ `local_qa`), `generation_supported=false` e `requires_external_api_key=false` impostos por validação; naquela frente ainda não registrado no `provider_registry` (registrado default-off na suíte posterior); nenhum backend instalado, nenhuma rede.
- **Evaluation Foundation** (`apps/api/app/modules/evaluation/`): `EvaluationCheck`/`EvaluationResult`; `evaluate_intelligence_plan` (checks: provider real bloqueado, sem auto-training, sem fine-tuning, sem exposição de `.env`/segredo, revisão humana para release gate, memória ≠ treinamento) e `evaluate_report_signals` (sinais críticos/altos exigem revisão humana).
- **Task types novos** no Task Router (`report_ingestion`, `project_memory_summary`, `model_foundation_review`, `intelligence_planning`; criticidade `medium`, `allow_mock=true`), permitidos apenas para `origin_system=pedrocore` — FinGuard não recebeu tasks novas.
- **Documentação**: `docs/14-intelligence-layer/` (4 documentos) + `docs/13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01.md`; README/VERSION/status/roadmap/mapeamento/MOCs/decisões atualizados.
- **Testes**: `test_intelligence_layer.py`, `test_report_intelligence.py`, `test_local_model_contract.py`, `test_evaluation_foundation.py` — 41 novos. Suíte: `257 passed, 6 skipped, 2 warnings` (skips/warnings pré-existentes).

### Não alterado / não feito

- Nenhuma rota nova; contratos `ChatResponse`/`OrchestrateResponse` intactos (teste dedicado confirma).
- Sem provider real, sem `allow_real_provider=true`, sem `.env`, sem FinGuard, sem treinamento/fine-tuning/autoaprendizado, sem download de modelo, sem banco persistente novo, sem RAG.
- Sem push, tag ou merge.

## PEDROCORE-DOCFIX-OBSIDIAN-07 — Mapeamento completo e saneamento documental

Status: documentação atualizada nesta tarefa, sem alteração de código de produção.

### Motivo

Após o fechamento local `v7.0.0`, alguns documentos históricos ainda descreviam como "futuro" ou "não implementado" recursos já existentes no lado PedroCore, como `/api/orchestrate`, Task Router, Project Context, Prompt Builder, QA textual local, Artifact Reader opt-in, policy enforcement forte e integração FinGuard controlada.

### Corrigido

- Criado `docs/00_MAPEAMENTO_GERAL_PEDROCORE.md` com visão completa de endpoints, módulos, fluxo, QA textual, release gate, policy, providers, safe mode, Artifact Reader, Visual QA, OCR, Playwright, exploration, audit, integração FinGuard, testes, estado Git/versionamento, pendências, riscos e melhorias opcionais.
- Criados MOCs Obsidian: `MOC_PEDROCORE_IA`, `MOC_ARQUITETURA`, `MOC_SEGURANCA`, `MOC_QA_RELEASE_GATE`, `MOC_INTEGRACOES`, `MOC_TESTES`, `MOC_VERSOES_STATUS`.
- `README.md`, `VERSION.md` e `docs/09_STATUS_ATUAL.md` alinhados com `v7.0.0`.
- Documentos históricos de contratos, arquitetura, QA Intelligence, visão geral e roadmap receberam notas de status atual para separar planejamento antigo do estado implementado.

### Não alterado

- Sem mudança de código de produção.
- Sem mudança de testes.
- Sem provider real.
- Sem leitura/acesso ao FinGuard.
- Sem `.env`.
- Sem push, merge, commit ou tag.

## PEDROCORE-IMPLEMENT-05 + PEDROCORE-FINALIZE-06 — Integrações reais controladas e fechamento final local

Status: implementadas e commitadas em subfrentes (`33a7dc2` 05A, `790e1b4` 05B, `70afba1` 05C, `b3f1be5` 05D, `2670040` 05E, `3bcfa05` 05F, `e08c519` 06A, + commit documental 06B). Fechamento final: `docs/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md`.

- **05A — Flags/guards/testes opt-in:** módulo `real_features/` (todas as flags reais `false` por padrão; `PEDROCORE_ENFORCE_PROJECT_POLICY` e `PEDROCORE_RELEASE_REQUIRE_HUMAN_REVIEW_FOR_REAL_FEATURES` default `true`); 28 warning codes novos; helper `tests/real_flags.py`; 6 testes reais opt-in SKIPPED por padrão; 14 variáveis novas no `.env.example`.
- **05B — FinGuard controlado:** módulo `policy_enforcement/` com bloqueio real (task perigosa, payload com comando, task crítica não permitida, origem desconhecida crítica) e curto-circuito na orquestração (`status=blocked`, provider nunca chamado); `pedrocore` passou a permitir tasks QA localmente; contrato final em `docs/11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO.md`.
- **05C — Artifact Reader final:** consolidado com 4 testes extras (`.env` aninhado `apps/api/.env`, variantes `.env.*`, orçamento total no serviço e em requisição multi-arquivo).
- **05D — OCR local opt-in:** módulo `ocr/` (`OCR_NOT_ENABLED`/`OCR_DEPENDENCY_UNAVAILABLE`/execução local com sanitização de segredo e revisão humana); dependência não instalada; status refletido no `visual_qa_analysis`.
- **05E — Multimodal guard:** `evaluate_real_visual_guard` — três condições cumulativas (flag multimodal, flag visual QA, `allow_real_provider`) e, mesmo com todas, contrato-somente (`REAL_FEATURE_REQUIRES_HUMAN_CONFIRMATION`); nenhuma imagem é enviada a provider externo nesta versão.
- **05F — Playwright read-only opt-in:** `exploration/playwright_adapter.py` — allowlist de base URLs, URLs FinGuard sempre bloqueadas, ações interativas (`click`/`type_text`/`submit`/`login`) sempre bloqueadas, navegação read-only só com flag + dependência instalada pelo humano.
- **06A — Enforcement final:** somente `local_qa` aprova release gate (`RELEASE_GATE_TRUSTED_PROVIDERS`); provider real → `RELEASE_REQUIRES_HUMAN_REVIEW`; policy forte por padrão.
- **Testes:** `216 passed, 6 skipped (opt-in), 2 warnings` (warnings pré-existentes Starlette/Pydantic). 50 testes novos nesta frente.
- **Não alterado:** `apps/web`, `.env`, `apps/api/.env`; FinGuard real não acessado; sem push; `v6.0.0` preservada em `ee2ac68`. Bloco 12 permanece cancelado.

## PEDROCORE-IMPLEMENT-04 — Expansão operacional segura (Blocos 8–11)

Status: implementada, em validação nesta frente.

### Bloco 8 — Contrato FinGuard → PedroCore (payload fake)

- `project_context/service.py` — `finguard-local` adicionado; `allowed_tasks` do FinGuard e do PedroCore ganharam as tasks exploratórias; notas atualizadas; novo conjunto `FINGUARD_ORIGIN_SYSTEMS`.
- `docs/11-integracoes/CONTRATO_FINGUARD_PEDROCORE.md` — contrato completo (payloads fake, resposta, segurança, limitações, integração real futura, confirmações explícitas de não-acesso ao FinGuard).
- Origem FinGuard nunca usa o Artifact Reader (bloqueio na orquestração + bloqueio de caminhos contendo "finguard" no próprio reader).

### Bloco 9 — Artifact Reader real controlado por allowlist

- Novo módulo `apps/api/app/modules/artifact_reader/` (`ArtifactReadResult`, `ArtifactReaderService.read`): desabilitado por padrão (`PEDROCORE_ARTIFACT_READER_ENABLED=false`), allowlist de diretórios, extensões `.txt,.md,.log,.json,.csv`, limites 20k/100k chars; bloqueia path traversal, `.env`, binário (byte nulo/decode), segredo identificável (regex de atribuição senha/token/chave e chaves privadas), arquivo grande e caminho FinGuard. Nunca escreve/deleta/executa.
- `orchestration/service.py` — `_apply_artifact_reader`: com reader habilitado e path allowlisted, o arquivo lido vira artefato textual (`ARTIFACT_READER_USED`) e passa pelos limites/QA normais; qualquer falha mantém a rejeição pré-existente (`ARTIFACT_PATH_REJECTED`). Audit continua sem conteúdo.
- `.env.example` — 5 variáveis novas do reader, sem valor real.
- Novos códigos `ARTIFACT_READER_*` (10) em `contracts/codes.py` com severidades (env/secret = `critical`).

### Bloco 10 — QA visual stub (sem OCR, sem provider multimodal, sem Playwright)

- Novo módulo `apps/api/app/modules/visual_qa/` (`VisualQAAnalysis`, `VisualQAService.analyze`): para artefatos visuais gera análise conservadora `not_analyzed`/`stub` com `requires_human_review=true`, `can_advance=false`, `suggested_manual_checks` e flags explícitas `ocr_attempted=false`, `provider_attempted=false`, `playwright_attempted=false`.
- `/api/orchestrate` ganhou campo `visual_qa_analysis`; release gate nunca avança apenas com evidência visual (`VISUAL_QA_BLOCKED_FOR_RELEASE_GATE`).
- Novos códigos `VISUAL_QA_*` (4).

### Bloco 11 — Agente exploratório assistido (plano/manual)

- Novo módulo `apps/api/app/modules/exploration/` (`ExplorationPlan`, `ExplorationService.build`): plano determinístico local com `exploration_plan`, `manual_steps` (a partir de `context.routes`), `risk_areas` (heurística de keywords), `required_evidence`, `human_confirmations`, `blocked_actions` e sempre `can_execute_actions=false`, `can_advance=false`, `requires_human_review=true`; pedidos destrutivos geram `EXPLORATION_ACTION_BLOCKED`.
- `task_router/service.py` — 3 novas strategies (`exploratory_test_plan`, `manual_exploration_report`, `assisted_exploration_review`, response_style `exploration_plan_structured`).
- `/api/orchestrate` ganhou campo `exploration`. `/api/chat` permanece com contrato inalterado.
- Novos códigos `EXPLORATION_*`/`HUMAN_CONFIRMATION_REQUIRED` (6).

### Testes

- Novos: `tests/test_finguard_contract.py` (10), `tests/test_artifact_reader.py` (13), `tests/test_visual_qa.py` (7), `tests/test_exploration.py` (10); `tests/test_project_context.py` atualizado (finguard allowed_tasks/notes + finguard-local, +1 teste).
- **Comando:** `./.venv/Scripts/python.exe -m pytest -q` (em `apps/api`). **Resultado:** `166 passed, 2 warnings` (warnings pré-existentes Starlette/Pydantic). Testes de reader usam apenas `tmp_path`; nenhum teste chama provider real, faz request externo, executa OCR ou Playwright.

### Não alterado / bloqueado por decisão

- `apps/web`, `.env` e `apps/api/.env` intocados. FinGuard real não acessado. Bloco 12 cancelado (Decisão 060). Sem tag, sem push.

## PEDROCORE-DOCFIX-05 — Correção documental pós-tag v6.0.0

Status: correção documental pós-auditoria.

### Motivo

A auditoria pós-tag classificou o MVP como `APROVADO COM RESSALVAS`: o backend estava correto, mas alguns documentos ainda tratavam `v6.0.0` como futura/inexistente.

### Corrigido

- Documentação ajustada para registrar que a tag anotada `v6.0.0` já existe.
- Tag `v6.0.0` registrada como apontando para `ee2ac68`.
- Mensagem da tag registrada: `v6.0.0 - MVP backend PedroCore IA`.
- Status ajustado para deixar claro que `v6.0.0` fecha o MVP backend, não o projeto completo.
- Blocos 7–11 do planejamento maior, Bloco 12 e Blocos 13–15 finais permanecem não implementados.

### Não alterado

- Sem alteração funcional de backend.
- Sem alteração de testes.
- Sem alteração de frontend/design.
- Sem alteração de `.env`.
- Sem criação, movimentação ou exclusão de tag.
- Sem push.

## PEDROCORE-IMPLEMENT-03 — MVP backend (Blocos 1–7): QA textual real, release gate, /api/orchestrate, safe mode

Status: implementada, validada e commitada em `6ed4c41`.

### Motivação

Evoluir o PedroCore de "QA skeleton sem análise real" para um MVP operacional: análise textual QA local e determinística, release gate conservador, endpoint operacional `/api/orchestrate`, safe mode de providers reais, autenticação interna opcional, contrato padronizado de warnings/errors e audit não persistente completo.

### Backend — Criado

- `apps/api/app/modules/contracts/codes.py` — códigos padronizados de warning/error (`QA_NO_ARTIFACTS`, `QA_FALLBACK_MOCK`, `PROJECT_TASK_NOT_ALLOWED`, `UNKNOWN_ORIGIN_SYSTEM`, `ARTIFACT_VISUAL_UNSUPPORTED`, `ARTIFACT_TRUNCATED`, `ARTIFACT_PATH_REJECTED`, `PROVIDER_REAL_BLOCKED`, `INTERNAL_AUTH_*`, `RELEASE_GATE_BLOCKED`, `QA_RISK_CRITICAL`, `QA_FAILURE_DETECTED`, `QA_ERROR_DETECTED`, `QA_WARNING_DETECTED`, `QA_ARTIFACT_LIMIT_EXCEEDED`), severidades (`info`/`warning`/`error`/`critical`) e schema `WarningItem`.
- `apps/api/app/modules/qa_analysis/` — `QATextAnalyzer` local determinístico: detecta sucesso/falha/erro/warning/build-lint-typecheck e risco crítico (produção, banco real, drop/truncate/delete from, secret/token/senha/api key/.env, deploy) por regex com word boundaries; classifica `risk_level` (low/medium/high/critical), calcula `confidence` (0–1, nunca 1.0), decide `can_advance` conservador e gera `suggested_commands`/`suggested_fixes` apenas seguros. Sem IA externa, sem rede, sem leitura de arquivo, sem execução de comando.
- `apps/api/app/modules/orchestration/` — `OrchestrationService` centraliza o pipeline (Task Router → Project Context → Policy → Artifacts → Provider com safe mode → QA Analyzer → QA Response/Release Gate → Audit), consumido por `/api/chat` e pelo novo `POST /api/orchestrate` (resposta estruturada com `status`, `warnings` com severidade, `warning_codes`, `error_code`, `blocked_reason`, `qa`, `release_gate`, `audit` completo). Pseudo-provider local `local_qa` responde sem chamada externa.

### Backend — Alterado

- `artifacts/` — limites `MAX_ARTIFACTS=10`, `MAX_ARTIFACT_CONTENT_CHARS=20000`, `MAX_TOTAL_ARTIFACT_CHARS=100000` com truncamento e warnings; rejeição de metadata com campos de path (`path`, `file_path`, `absolute_path`, `relative_path`, `filesystem_path`, `local_path`, `directory`, `folder`, `glob`) sem nunca ler arquivo; novos campos `warning_codes`, `analysis_text`, `textual_count`, `rejected_count`, `path_rejected`, `truncated`.
- `qa_response/` — `QAResponseSkeleton` preenchido com dados reais do analyzer (`analysis_source="local_text_heuristic"`), com guardas conservadoras de `can_advance`; novo `evaluate_release_gate(...)` → `ReleaseGateResult` (`can_advance`, `blocked_reason`, `risk_level`, `confidence`): bloqueia sem artifacts, com path rejeitado, truncamento, falha/erro, risco high/critical, fallback Mock, safe mode ou provider mock em release gate; só libera com evidência textual limpa, risco low e confiança ≥ 0.6 via análise local.
- `audit/schemas.py` — `AuditMetadata` estendido: `provider_used`, `safe_mode_blocked`, `status`, `latency_ms`, `risk_level`, `can_advance`; continua não persistente (memória, devolvido só na resposta, sem conteúdo de artifacts/segredos).
- `chat/schemas.py` — `ChatRequest.allow_real_provider` (default `False`); `ChatResponse` ganhou `warning_codes`, `safe_mode_blocked`, `status`, `blocked_reason`, `error_code` (defaults compatíveis).
- `chat/service.py` — passou a delegar ao `OrchestrationService`; contrato legado 100% preservado; `/api/chat` continua sem exigir API key.
- `main.py` — inclui o router de orquestração (`POST /api/orchestrate`).
- `.env.example` — adicionada `PEDROCORE_INTERNAL_API_KEY=""` (sem valor real). `.env` real não foi tocado.

### Safe mode e autenticação

- `allow_real_provider=false` por padrão (ausente = false): Gemini/OpenAI/Claude/DeepSeek/Grok nunca são chamados sem autorização explícita; bloqueio gera fallback Mock com `PROVIDER_REAL_BLOCKED`, `provider_requested`/`provider_used`, `fallback_used=true`, `safe_mode_blocked=true`; em `release_gate_review` o bloqueio impede avanço (`RELEASE_GATE_BLOCKED`).
- `POST /api/orchestrate` com auth interna opcional: se `PEDROCORE_INTERNAL_API_KEY` configurada, exige header `X-PedroCore-Api-Key` (ausente → 401 `INTERNAL_AUTH_MISSING`; errado → 401 `INTERNAL_AUTH_INVALID`); sem chave configurada, modo dev/local com warning `INTERNAL_AUTH_NOT_CONFIGURED`. A chave nunca é retornada. `/api/chat` continua livre.

### Testes

- Novos: `tests/test_qa_analysis.py` (21), `tests/test_release_gate.py` (13), `tests/test_orchestrate_api.py` (13), `tests/test_safe_mode.py` (6); `tests/test_artifacts.py` ganhou 6 testes (truncamento, limite de quantidade, limite total, rejeição de path incluindo arquivo real em disco nunca lido).
- **Comando:** `./.venv/Scripts/python.exe -m pytest -q` (em `apps/api`). **Resultado:** `125 passed, 2 warnings` (66 anteriores preservados sem alteração + 59 novos). Nenhum teste chama provider real, depende de chave real ou faz request de rede.

### Ainda não existe

Integração real com FinGuard, leitura real de arquivos, execução de comandos pelo PedroCore, QA visual real, OCR, Playwright, agente exploratório, dashboard, log persistente, provider real liberado em fluxo crítico, Blocos 7–11 do planejamento maior, Bloco 12 e Blocos 13–15 finais.

## PEDROCORE-IMPLEMENT-02 — QA textual foundation

Status: implementada, validada.

### Motivação

Com `PEDROCORE-IMPLEMENT-01C/01D/01E/01F/01G/01H` commitada em `95cbfab` (correção documental em `1ff1758`), esta etapa evolui a base de orquestração para suportar policy de tarefas por projeto, recebimento de artefatos textuais por payload e um skeleton seguro de resposta QA — sem implementar QA Intelligence real, sem ler arquivos e sem integração real com o FinGuard.

### Backend — Criado

- `apps/api/app/modules/artifacts/__init__.py`, `schemas.py`, `service.py` — `ArtifactInput`/`ArtifactProcessingResult` e `ArtifactService.process(artifacts)`: aceita 9 tipos textuais (`markdown`, `qa_report`, `log`, `terminal_output`, `json_result`, `documentation`, `changelog`, `pending_list`, `text`), sinaliza tipos visuais (`screenshot`, `image`, `playwright_trace`) como não suportados sem tentar analisá-los, gera warning para conteúdo vazio e para tipo desconhecido, e produz `text_block` para o Prompt Builder. Não lê arquivo, não aceita path como instrução de leitura.
- `apps/api/app/modules/qa_response/__init__.py`, `schemas.py`, `service.py` — `QAResponseSkeleton` e `QAResponseService.build_skeleton(...)`: retorna skeleton apenas para `qa_report_analysis`/`qa_failure_diagnosis`/`release_gate_review`, sempre `status="not_analyzed"`, `risk_level="unknown"`, `can_advance=False`, `confidence=0.0`, listas de achados vazias e warnings explicando ausência de análise real, fallback crítico e artefatos ausentes/visuais.

### Backend — Alterado

- `apps/api/app/modules/project_context/schemas.py`/`service.py` — `TaskPolicyResult` e `ProjectContextResolver.evaluate_task_policy(project, task_type)`: task listada em `allowed_tasks` → permitida sem warning; fora da lista → warning de cautela sem bloquear; lista vazia/projeto `unknown` → permitida com warning específico.
- `apps/api/app/modules/prompt_builder/schemas.py`/`service.py` — `PromptBuildInput.artifacts_text_block` e nova seção `[Artefatos enviados]` no prompt enriquecido (conteúdo recebido ou aviso de ausência), sem interpretação/resumo automático.
- `apps/api/app/modules/chat/schemas.py` — `ChatRequest.artifacts` opcional; `ChatResponse` ganhou `task_allowed_for_project`, `artifact_count`, `artifact_types`, `artifact_warnings`, `qa_skeleton`.
- `apps/api/app/modules/chat/service.py` — `ChatService.send_message` passou a avaliar a policy de `allowed_tasks`, processar `payload.artifacts`, repassar o bloco textual ao Prompt Builder e construir o `qa_skeleton` (sucesso e fallback); `task_warnings` agora agrega também os warnings de policy e de artefatos, incluindo o warning de "QA sem artefatos" para tarefas críticas.

### Testes

- `apps/api/tests/test_artifacts.py` — 6 testes: sem artefatos, markdown com conteúdo, artefato sem conteúdo, artefato visual, tipo desconhecido, metadata incluída no bloco textual.
- `apps/api/tests/test_qa_response.py` — 4 testes: skeleton `not_analyzed` para task QA, `None` para task não-QA, warning de fallback crítico propagado, warning de artefato visual propagado.
- `apps/api/tests/test_qa_flow.py` — 13 testes de API: compatibilidade retroativa, artefato markdown/qa_report aceitos, artefato sem conteúdo, artefato visual, tipo desconhecido, `finguard`+`qa_report_analysis` permitido, `finguard`+`general_chat` com warning, origem desconhecida com warning de policy, QA sem artefatos com warning, `release_gate_review` com fallback e skeleton, task não-QA sem skeleton, `/api/providers`.
- `apps/api/tests/test_project_context.py` — 4 testes novos de policy (`evaluate_task_policy`): task permitida, task não listada, projeto desconhecido, lista vazia em projeto conhecido.
- `apps/api/tests/test_prompt_builder.py` — 2 testes novos: seção de artefatos presente com conteúdo, ausência de artefatos relatada explicitamente.
- **Comando rodado:** `./.venv/Scripts/python.exe -m pytest -v` (dentro de `apps/api`).
- **Resultado:** `66 passed, 2 warnings` (37 testes anteriores + 29 novos; warnings pré-existentes de deprecação do Starlette/Pydantic, não introduzidos por esta mudança).

### Compatibilidade

- `POST /api/chat` continua aceitando requisições antigas sem `artifacts`, com todos os campos novos tendo defaults seguros.
- `GET /api/providers` inalterado.
- Nenhum endpoint novo foi criado — nenhuma menção a `/api/orchestrate` existe no código.
- `can_advance` nunca é `True` no skeleton — sempre `False` nesta etapa.

### Não alterado nesta etapa

- Sem alterações de frontend, componentes, estilos, layout ou design (`apps/web` limpo).
- Sem alterações no `.env`.
- Sem chamadas a providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok) — testes usam apenas Mock e provider inexistente.
- Sem leitura ou escrita no repositório do FinGuard.
- Sem instalação de dependências.
- Sem Artifact Reader real (leitura automática de arquivo), QA Intelligence real, análise visual real, endpoint de orquestração, banco de dados/persistência ou autenticação entre sistemas.
- Sem alteração de versão de produto (V5.1.9) ou versão de pacote backend (0.2.0).
- Sem commit e sem criação de tag até esta etapa.

## PEDROCORE-IMPLEMENT-01C/01D/01E/01F/01G/01H — Base interna de orquestração expandida

Status: implementada, validada.

### Motivação

Com `PEDROCORE-IMPLEMENT-01A/01B` (Task Router mínimo) commitada em `577bc88`, esta etapa evolui o fluxo interno de `/api/chat` para uma primeira base real de orquestração: resolução de contexto por projeto, montagem de prompt enriquecido, metadados estruturais de resposta e auditoria não persistente — sempre operando dentro do endpoint já existente, sem endpoint novo e sem tocar em sistemas externos.

### Backend — Criado

- `apps/api/app/modules/project_context/__init__.py`, `schemas.py`, `service.py` — `ProjectContext` (project_id, display_name, read_only, can_execute_commands, can_write_files, allowed_tasks, warnings, notes) e `ProjectContextResolver.resolve(origin_system)`, resolvendo `pedrocore`, `finguard` e `unknown` a partir de configuração interna.
- `apps/api/app/modules/prompt_builder/__init__.py`, `schemas.py`, `service.py` — `PromptBuildInput`/`PromptBuildResult` e `PromptBuilder.build(...)`, montando `enriched_system_prompt` com seções de instrução, tarefa, origem, limites do projeto, contexto, metadata e regras de segurança (incluindo regra específica para `origin_system=finguard`).
- `apps/api/app/modules/audit/__init__.py`, `schemas.py`, `service.py` — `AuditMetadata` (audit_id, timestamp, origin_system, task_type, provider_requested, fallback_used, criticality) e `AuditService.create(...)`, gerando dados em memória via `uuid.uuid4()` e `datetime.now(timezone.utc)`.

### Backend — Alterado

- `apps/api/app/modules/chat/schemas.py` — `ChatResponse` ganhou `project_id`, `project_read_only`, `project_can_execute_commands`, `project_can_write_files`, `response_style`, `audit_id`, `audit_timestamp`, todos com defaults seguros.
- `apps/api/app/modules/chat/service.py` — `ChatService.send_message` passou a resolver `ProjectContext` após o Task Router, gerar `AuditMetadata` no início da request, chamar o Prompt Builder e usar `enriched_system_prompt` na chamada ao provider (sucesso e fallback); `task_warnings` agora agrega os warnings do Task Router e do Project Context; `audit.fallback_used` é atualizado no fim de cada caminho.

### Testes

- `apps/api/tests/test_project_context.py` — 5 testes: resolve `pedrocore`, resolve `finguard` (somente leitura, sem execução/escrita), sistema desconhecido retorna `unknown` com warning, normalização de case/espaço e defaults, resolver só devolve dados.
- `apps/api/tests/test_prompt_builder.py` — 9 testes: monta prompt sem chamar provider, inclui task_type/origin_system, inclui context/metadata quando enviados (e informa ausência quando não enviados), inclui criticidade para `qa_report_analysis`, inclui limites do projeto, inclui regra de segurança do FinGuard (presença e ausência), preserva `system_prompt` customizado.
- `apps/api/tests/test_orchestration_flow.py` — 8 testes: request legada com defaults de orquestração, `origin_system=finguard` retorna metadados de projeto, origem desconhecida retorna warning, fallback crítico mantém warning forte e gera audit, tarefa crítica mantém `requires_structured_response`, `audit_id`/`audit_timestamp` presentes e únicos por request, `/api/providers` continua funcionando, guarda de que a suíte usa apenas providers seguros (`mock`/inexistente).
- **Comando rodado:** `./.venv/Scripts/python.exe -m pytest -v` (dentro de `apps/api`).
- **Resultado:** `37 passed, 2 warnings` (15 testes anteriores + 22 novos; warnings pré-existentes de deprecação do Starlette/Pydantic, não introduzidos por esta mudança).

### PEDROCORE-IMPLEMENT-01I — avaliada, adiada

Não foi criado `apps/api/app/modules/orchestration/`. Justificativa: `ChatService.send_message` já encapsula o pipeline completo (Task Router → Project Context → Audit → Prompt Builder → Provider → fallback) em um único ponto de entrada reutilizável; extrair um módulo de orquestração agora seria abstração prematura sem um segundo consumidor real (ex.: um futuro endpoint `/api/orchestrate`, que **não** foi criado nesta etapa). Registrado como pendência (Decisão Técnica 044).

### Compatibilidade

- `POST /api/chat` continua aceitando requisições antigas, com todos os campos novos tendo defaults seguros.
- `GET /api/providers` inalterado.
- Nenhum endpoint novo foi criado.
- `BaseAIProvider.build_prompt` continua existindo; providers reais não foram reescritos.

### Não alterado nesta etapa

- Sem alterações de frontend, componentes, estilos, layout ou design (`apps/web` limpo).
- Sem alterações no `.env`.
- Sem chamadas a providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok).
- Sem leitura ou escrita no repositório do FinGuard.
- Sem instalação de dependências.
- Sem Artifact Reader real, QA Intelligence real, análise visual, banco de dados/persistência ou autenticação entre sistemas.
- Sem alteração de versão de produto (V5.1.9) ou versão de pacote backend (0.2.0).
- Sem commit e sem criação de tag.

## PEDROCORE-IMPLEMENT-01A/01B — Task Router mínimo + metadados de resposta

Status: implementada, validada.

### Motivação

Com `PEDROCORE-REPLAN-01` concluída no escopo documental (commit `cc808a7`), esta é a primeira implementação de código pós-reformulação: uma base mínima e segura de orquestração por `task_type`, operando dentro do endpoint `/api/chat` já existente, sem quebrar compatibilidade e sem chamar provider real nos testes.

### Backend — Criado

- `apps/api/app/modules/task_router/__init__.py`
- `apps/api/app/modules/task_router/schemas.py` — `TaskStrategy` (task_type, response_style, requires_structured_response, criticality, allow_mock, warnings).
- `apps/api/app/modules/task_router/service.py` — `TaskRouter.resolve()`, normaliza `task_type`, reconhece `general_chat`, `technical_explanation`, `code_help`, `qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `artifact_summary` e `unknown`.

### Backend — Alterado

- `apps/api/app/modules/chat/schemas.py` — `ChatRequest` ganhou `task_type` (default `"general_chat"`), `origin_system` (default `"pedrocore"`), `context` e `metadata` (opcionais); `ChatResponse` ganhou `task_type`, `origin_system`, `task_criticality`, `requires_structured_response`, `task_warnings`.
- `apps/api/app/modules/chat/service.py` — `ChatService.send_message` chama `task_router.resolve()` antes de resolver o provider; resposta (sucesso e fallback) inclui os novos metadados; warning forte adicionado quando `fallback_used=True` em tarefa crítica (`qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`) ou quando Mock é usado em tarefa com `allow_mock=False`.

### Testes

- `apps/api/tests/test_task_router.py` — 8 testes novos: requisição antiga sem `task_type` continua funcionando; `general_chat` retorna `task_type` correto; `qa_report_analysis` retorna `requires_structured_response=true`/`criticality="high"`/warning; `release_gate_review` com provider desconhecido cai para Mock com `fallback_used=true` e warning forte; `task_type` desconhecido normaliza para `unknown` com warning sem quebrar; normalização de case/espaço no Task Router; defaults do Task Router; `/api/providers` continua funcionando.
- **Comando rodado:** `./.venv/Scripts/python.exe -m pytest -v` (dentro de `apps/api`).
- **Resultado:** `15 passed, 2 warnings` (7 testes antigos + 8 novos; warnings pré-existentes de deprecação do Starlette/Pydantic, não introduzidos por esta mudança).

### Compatibilidade

- `POST /api/chat` continua aceitando requisições antigas sem `task_type`/`origin_system`/`context`/`metadata`, com defaults seguros.
- `GET /api/providers` inalterado.
- Fallback para `MockProvider` preservado.
- Nenhum endpoint `/api/orchestrate` foi criado — o Task Router opera internamente dentro de `/api/chat` (Decisão Técnica 039).

### Não alterado nesta etapa

- Sem alterações de frontend, componentes, estilos, layout ou design (`apps/web` limpo).
- Sem alterações no `.env`.
- Sem chamadas a providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok) — testes usam apenas Mock e provider inexistente.
- Sem leitura ou escrita no repositório do FinGuard.
- Sem instalação de dependências.
- Sem Prompt Builder real, Project Context real, Artifact Reader, QA Intelligence real ou Audit/logs.
- Sem alteração de versão de produto (V5.1.9) ou versão de pacote backend (0.2.0).
- Sem criação de tag.

## PEDROCORE-REPLAN-01E — Fechamento documental da reformulação

Status: em fechamento.

### Motivação

Com `01A` (visão oficial), `01B` (contratos técnicos), `01C` (arquitetura-alvo) e `01D` (QA Intelligence) concluídas e commitadas, a frente `01E` fecha documentalmente `PEDROCORE-REPLAN-01` inteira: consolida o que foi entregue, registra o que existe e o que ainda não existe no código, registra riscos remanescentes e pendências pós-reformulação, e recomenda a próxima fase de implementação.

### Criado

- `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md` — documento de fechamento: objetivo da frente, escopo executado (01A–01E), commits da frente, transição de visão (antes/agora), o que existe hoje no código, o que ainda não existe, documentos oficiais criados/consolidados, relação com o FinGuard, decisões arquiteturais consolidadas, riscos remanescentes, pendências pós-reformulação e próxima fase recomendada (`PEDROCORE-IMPLEMENT-01`).

### Alterado (documentação)

- `README.md` — adicionada seção "Estado atual da reformulação" (01A–01D concluídas, 01E em fechamento, implementação ainda não iniciada, frontend/design preservados, FinGuard não alterado).
- `VERSION.md` — frente atual atualizada para `PEDROCORE-REPLAN-01E`; status de fechamento documental; próxima fase sugerida (`PEDROCORE-IMPLEMENT-01`); versão de produto (V5.1.9) e versão backend (0.2.0) mantidas sem alteração.
- `docs/03-versoes/ROADMAP.md` — `01A`, `01B`, `01C` e `01D` marcadas como concluídas (commits `1e5a8cb`, `6e7badd`, `c1e7816`, `8c68b67`); `01E` marcada como concluída/em fechamento documental; `PEDROCORE-REPLAN-01` registrada como concluída no escopo documental; adicionada fase futura sugerida `PEDROCORE-IMPLEMENT-01` (ainda não iniciada).
- `docs/09_STATUS_ATUAL.md` — frente atual atualizada para `PEDROCORE-REPLAN-01E`; registrado que `01A`, `01B`, `01C` e `01D` estão concluídas/commitadas; registrado que, após commit da 01E, `PEDROCORE-REPLAN-01` fica concluída no escopo documental; próximo passo apontado para planejamento de `PEDROCORE-IMPLEMENT-01`.
- `docs/07-decisoes/DECISOES_TECNICAS.md` — adicionadas decisões 034 a 038, preservando as decisões 001 a 033.
- `docs/08_CHANGELOG.md` — esta entrada.

### Documentação legada/duplicada

Documentos antigos e duplicados em `docs/` (pares `0X_NOME.md`/`0X-nome/`, pastas vazias, arquivos `.bak-*` versionados) **não foram removidos** nesta etapa. Ficam registrados como pendência pós-reformulação, a ser tratada em frente futura específica de saneamento documental (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`, seção 11, e Decisão Técnica 035).

### Não alterado nesta etapa

- Sem alterações de código-fonte (`apps/api`, `apps/web`).
- Sem alterações de frontend, componentes, estilos, layout ou design.
- Sem instalação de dependências, sem execução de servidor ou testes.
- Sem chamadas a providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok).
- Sem alterações no `.env`.
- Sem leitura ou escrita no repositório do FinGuard, e sem execução de comandos dentro dele.
- Sem remoção de documentos antigos/duplicados.
- Sem commit e sem criação de tag.

## PEDROCORE-REPLAN-01D — Planejamento de QA Intelligence

Status: iniciada.

### Motivação

Com a arquitetura-alvo documentada em `PEDROCORE-REPLAN-01C` (commit `c1e7816`), a frente `01D` documenta especificamente a camada futura de QA Intelligence: como o PedroCore poderia apoiar sistemas externos, especialmente o QA Automation do FinGuard, na análise inteligente de relatórios, logs, evidências e falhas, e na recomendação assistida de avanço/bloqueio de release.

### Criado

- `docs/12-qa-intelligence/QA_INTELLIGENCE_OVERVIEW.md` — definição de QA Intelligence, relação com o QA Automation do FinGuard, artefatos analisáveis (12 tipos), planejamento de relatórios QA Markdown, tabela de casos de uso, resposta estruturada de QA, severidade/risco, regra de avanço/bloqueio, fallback Mock em QA, análise visual/exploratória futura, limites/proibições e relação com a arquitetura-alvo (01C).
- `docs/12-qa-intelligence/QA_REPORT_ANALYSIS.md` — caso de uso `qa_report_analysis`.
- `docs/12-qa-intelligence/QA_FAILURE_DIAGNOSIS.md` — caso de uso `qa_failure_diagnosis`, com reforço da diferença entre diagnóstico e correção.
- `docs/12-qa-intelligence/QA_RELEASE_GATE.md` — caso de uso `release_gate_review`, incluindo a regra de avanço/bloqueio assistido (`can_advance`).

### Alterado (documentação)

- `docs/03-versoes/ROADMAP.md` — `PEDROCORE-REPLAN-01A`, `01B` e `01C` marcadas como concluídas (commits `1e5a8cb`, `6e7badd` e `c1e7816`); `01D` marcada como em andamento; `01E` mantida como planejada; adicionada referência aos documentos de `docs/12-qa-intelligence/`.
- `docs/09_STATUS_ATUAL.md` — frente atual atualizada para `PEDROCORE-REPLAN-01D`; registrado que `01A`, `01B` e `01C` estão concluídas/commitadas; reforçado que QA Intelligence, leitura real de arquivos do FinGuard e análise visual real continuam sem implementação em código.
- `docs/07-decisoes/DECISOES_TECNICAS.md` — adicionadas decisões 028 a 033, preservando as decisões 001 a 027.
- `docs/08_CHANGELOG.md` — esta entrada.

### Não alterado nesta etapa

- Sem alterações de código-fonte (`apps/api`, `apps/web`).
- Sem criação de endpoint, schema Pydantic, parser de relatório, classificador de risco ou lógica de diagnóstico.
- Sem alterações de frontend, componentes, estilos, layout ou design.
- Sem instalação de dependências, sem execução de servidor ou testes.
- Sem chamadas a providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok).
- Sem alterações no `.env`.
- Sem leitura ou escrita no repositório do FinGuard, e sem execução de comandos dentro dele.
- Sem commit e sem criação de tag.

## PEDROCORE-REPLAN-01C — Arquitetura-alvo: Task Router, Prompt Builder e Project Context

Status: iniciada.

### Motivação

Com os contratos técnicos documentados em `PEDROCORE-REPLAN-01B` (commit `6e7badd`), a frente `01C` documenta a arquitetura-alvo que permitiria implementar esses contratos no futuro: como uma requisição de orquestração seria classificada, contextualizada, transformada em prompt, executada por um provider e registrada em auditoria.

### Criado

- `docs/11-arquitetura-alvo/ARQUITETURA_ALVO_PEDROCORE.md` — arquitetura atual (FastAPI, `ChatService`, `ProviderRegistry`, `BaseAIProvider`, providers, fallback) vs. arquitetura-alvo (fluxo completo Task Router → Project Context → Artifact Reader → Prompt Builder → Provider Orchestration → Structured Responses → Audit/logs), além de Provider Orchestration, Structured Responses, Artifact Reader, Audit/logs, relação com `/api/chat` e relação com o FinGuard.
- `docs/11-arquitetura-alvo/TASK_ROUTER.md` — responsabilidade futura do Task Router e exemplos de roteamento planejados por `task_type`.
- `docs/11-arquitetura-alvo/PROMPT_BUILDER.md` — responsabilidade futura do Prompt Builder e a regra "Task Router decide, Prompt Builder monta, Provider executa".
- `docs/11-arquitetura-alvo/PROJECT_CONTEXT.md` — conceito planejado de representação de sistemas externos (ex.: FinGuard), com exemplo ilustrativo de campos conceituais.

### Alterado (documentação)

- `docs/03-versoes/ROADMAP.md` — `PEDROCORE-REPLAN-01A` e `01B` marcadas como concluídas (commits `1e5a8cb` e `6e7badd`); `01C` marcada como em andamento; `01D` e `01E` mantidas como planejadas; adicionada referência aos documentos de `docs/11-arquitetura-alvo/`.
- `docs/09_STATUS_ATUAL.md` — frente atual atualizada para `PEDROCORE-REPLAN-01C`; registrado que `01A` e `01B` estão concluídas/commitadas; reforçado que Task Router, Prompt Builder, Project Context, Artifact Reader, Provider Orchestration avançada, Structured Responses e Audit/logs continuam sem implementação em código.
- `docs/07-decisoes/DECISOES_TECNICAS.md` — adicionadas decisões 022 a 027, preservando as decisões 001 a 021.
- `docs/08_CHANGELOG.md` — esta entrada.

### Não alterado nesta etapa

- Sem alterações de código-fonte (`apps/api`, `apps/web`).
- Sem criação de endpoint, schema Pydantic, service, migration, banco de dados ou artifact reader real.
- Sem alterações de frontend, componentes, estilos, layout ou design.
- Sem instalação de dependências, sem execução de servidor ou testes.
- Sem chamadas a providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok).
- Sem alterações no `.env`.
- Sem leitura ou escrita no repositório do FinGuard.
- Sem commit e sem criação de tag.

## PEDROCORE-REPLAN-01B — Planejamento técnico e contratos

Status: iniciada.

### Motivação

Com a visão oficial consolidada em `PEDROCORE-REPLAN-01A` (commit `1e5a8cb`), a frente `01B` documenta os contratos técnicos que guiarão a evolução do PedroCore como orquestrador central: como sistemas externos poderiam futuramente enviar mensagem/contexto/tipo de tarefa e como o PedroCore devolveria uma resposta padronizada, incluindo o caso específico de análise de QA.

### Criado

- `docs/10-contratos/CONTRATOS_TECNICOS_PEDROCORE.md` — índice geral, estado atual vs. planejado e princípios de segurança/limites com o FinGuard.
- `docs/10-contratos/CONTRATO_ORQUESTRACAO.md` — contrato de entrada/saída planejado, campos obrigatórios/opcionais, tipos de tarefa (`task_type`), resposta padronizada, contrato de artefatos, `provider_preference`/roteamento e regras de fallback.
- `docs/10-contratos/CONTRATO_QA_INTELLIGENCE.md` — resposta estruturada planejada para tarefas de QA e relação de limites com o FinGuard.

### Alterado (documentação)

- `docs/03-versoes/ROADMAP.md` — `PEDROCORE-REPLAN-01A` marcada como concluída (commit `1e5a8cb`); `PEDROCORE-REPLAN-01B` marcada como em andamento; `01C`, `01D` e `01E` mantidas como planejadas; adicionada referência aos documentos de `docs/10-contratos/`.
- `docs/09_STATUS_ATUAL.md` — frente atual atualizada para `PEDROCORE-REPLAN-01B`; registrado que `01A` foi concluída/commitada; registrado que `01B` está em planejamento técnico/contratos; reforçado que Task Router, Prompt Builder, Artifact Reader e QA Intelligence continuam sem implementação em código.
- `docs/07-decisoes/DECISOES_TECNICAS.md` — adicionadas decisões 016 a 021, preservando as decisões 001 a 015.
- `docs/08_CHANGELOG.md` — esta entrada.

### Não alterado nesta etapa

- Sem alterações de código-fonte (`apps/api`, `apps/web`).
- Sem criação de endpoint, schema Pydantic, service, migration, banco de dados ou artifact reader real.
- Sem alterações de frontend, componentes, estilos, layout ou design.
- Sem instalação de dependências, sem execução de servidor ou testes.
- Sem chamadas a providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok).
- Sem alterações no `.env`.
- Sem leitura ou escrita no repositório do FinGuard.
- Sem commit e sem criação de tag.

## PEDROCORE-REPLAN-01A — Consolidação documental e visão oficial

Status: iniciada.

### Motivação

Uma auditoria somente leitura do repositório apontou duplicidade documental significativa (pares de arquivos conflitantes em `docs/`), uma visão de projeto desatualizada (PedroCore descrito apenas como chat pessoal multi-provider) e a necessidade de reposicionar o projeto como orquestrador central de IA do ecossistema Pedro, incluindo apoio futuro a inteligência operacional/QA de projetos externos como o FinGuard.

### Alterado (documentação)

- `README.md` — reescrito para apresentar o PedroCore como orquestrador central de IA, multi-provider, API para sistemas externos.
- `VERSION.md` — atualizado com a frente `PEDROCORE-REPLAN-01A` e status de reformulação documental.
- `docs/00-visao-geral/README.md` — reescrito como visão oficial consolidada.
- `docs/00-visao-geral/OBJETIVO.md` — objetivos atualizados (principal, secundário, futuro, fora de escopo).
- `docs/03-versoes/ROADMAP.md` — roadmap atualizado com entregas concluídas (V1 a V5.1.9) e a frente `PEDROCORE-REPLAN-01` (01A a 01E) e fases futuras.
- `docs/09_STATUS_ATUAL.md` — reescrito como status único, consolidando as seções repetidas anteriores.
- `docs/07-decisoes/DECISOES_TECNICAS.md` — adicionadas decisões 007 a 015, preservando as decisões 001 a 006.
- `docs/08_CHANGELOG.md` — esta entrada.

### Não alterado nesta etapa

- Sem alterações de código-fonte (`apps/api`, `apps/web`).
- Sem alterações de frontend, componentes, estilos, layout ou design.
- Sem instalação de dependências, sem execução de servidor ou testes.
- Sem chamadas a providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok).
- Sem alterações no `.env`.
- Sem leitura ou escrita no repositório do FinGuard.
- Documentação antiga/duplicada em `docs/` não foi removida nesta etapa — apenas sinalizada para consolidação em `PEDROCORE-REPLAN-01E`.

## V5.0.0 — Configurações de provider pela interface

Status: implementada para testes.

### Adicionado

- Painel dedicado de configuração de providers.
- Componente React `ProviderSettingsPanel`.
- Utilitário `providerSettings.ts`.
- Persistência local das preferências de provider.
- Chave `localStorage`: `pedrocore:v5:provider-settings`.
- Cards visuais para Mock, Gemini, OpenAI, Claude, DeepSeek e Grok/xAI.
- Status visual por provider:
  - `Mock local`;
  - `Configurado`;
  - `Sem chave`.
- Botão para restaurar modelo padrão do provider.
- Botão para restaurar prompt base padrão.
- Aviso visual de segurança sobre chaves no backend.
- Documento `docs/12_V5_CONFIG_PROVIDER.md`.
- Documento `docs/04-comandos/V5_COMANDOS.md`.

### Alterado

- `ChatPage.tsx` passou a carregar e salvar preferências de provider localmente.
- `ChatSidebar.tsx` passou a mostrar status do provider ativo.
- `global.css` recebeu estilos do painel de providers.
- `README.md`, `VERSION.md`, `COMANDOS_POWERSHELL.md` e documentação de status foram atualizados para V5.

### Mantido

- Backend FastAPI preservado.
- Providers existentes preservados.
- Estrutura multi-provider preservada.
- Fallback para MockProvider preservado.
- Histórico local da V3 preservado.
- Chave `pedrocore:v3:chat-history` preservada por compatibilidade.
- Nenhuma chave de API exposta no frontend.

### Não implementado

- Cadastro de chaves pela interface.
- Banco de dados.
- Login.
- RAG.
- Deploy.
- GitHub.
- Integração com FinGuard.

## V4.0.0 — Interface melhorada do chat

Status: aprovada e versionada localmente.

### Adicionado

- Sidebar de histórico local.
- Componentes React para interface do chat:
  - `ChatSidebar`;
  - `MessageBubble`;
  - `ChatComposer`;
  - `LoadingBubble`;
  - `ErrorBanner`.
- Bolhas modernas para usuário e IA.
- Métricas simples da conversa.
- Tratamento visual de erro com botão `Tentar novamente`.
- Loading visual `PedroCore está pensando...`.
- Documento `docs/11_V4_INTERFACE_CHAT.md`.
- Documento `docs/04-comandos/V4_COMANDOS.md`.

## V3.0.0 — Histórico local e feedback simples

Status: aprovada e versionada localmente.

### Adicionado

- Histórico local de mensagens usando `localStorage`.
- Feedback `Gostei` e `Não gostei` por resposta da IA.
- Botão para limpar histórico.
- Limite técnico de 100 mensagens salvas.
- Utilitários `chatStorage.ts`.
- Tipos `chat.ts`.

## V2.0.0 — Multi-provider com Gemini real

Status: aprovada e versionada localmente.

### Adicionado

- Estrutura multi-provider.
- GeminiProvider com chave real local.
- Providers estruturais para OpenAI, Claude, DeepSeek e Grok.
- Fallback para MockProvider.

## V1.0.4 — Correção definitiva dos textos da interface

Status: aprovada.

## V1 — Chat simples + API mock

Status: aprovada.

## V5.0.0 — Configurações de provider pela interface e logo oficial

### Adicionado

- Painel dedicado de configuração de providers.
- Cards visuais para Mock, Gemini, OpenAI, Claude, DeepSeek e Grok/xAI.
- Seleção de provider, modelo, modo e prompt base pela interface.
- Persistência local das preferências em `pedrocore:v5:provider-settings`.
- Logo oficial aplicada na sidebar e no avatar da IA.
- Favicon atualizado com a identidade visual oficial.

### Mantido

- Backend FastAPI sem alteração funcional.
- Histórico local da V3/V4 preservado em `pedrocore:v3:chat-history`.
- Chaves de API continuam somente no `.env` do backend.

### Fora do escopo

- Banco de dados.
- Login.
- RAG.
- GitHub.
- Deploy.
- Integração com FinGuard.

## V5.1.1 — Redesign real do front-end com logo oficial

### Corrigido

- A V5 anterior aplicava logo e configurações, mas não entregava o redesign visual aprovado.
- A V5.1 refaz a interface para aproximar o frontend do mockup aprovado pelo usuário.

### Adicionado

- Header de marca com logo oficial.
- Layout em console com sidebar, chat central e painel direito.
- Provider strip visível na área central.
- Painel de providers integrado ao desktop.
- Tema escuro, glassmorphism e gradientes alinhados ao mockup aprovado.

### Mantido

- Backend sem alteração funcional.
- Histórico e preferências locais preservados.
- `.env` fora do Git.


---

## V5.1.9 — Ajuste de CSS e logos dos providers

- Corrigido espaçamento e hierarquia do topo.
- Ajustado bloco de conversas recentes.
- Adicionado contador de histórico em badge.
- Adicionados ícones SVG internos para providers.
- Aplicados ícones no provider strip e no painel direito.


---

## V5.1.9 — Responsividade estrutural e configurações

- Corrigido layout para usar altura real do notebook.
- Removido scroll geral em desktop/notebook.
- Adicionada rolagem interna nos painéis.
- Corrigido botão Configurações para focar o painel direito.
- Mantidos logos e ícones dos providers.


---

## V5.1.9 — Responsividade preservada e topo limpo

- Retomada a base responsiva da V5.1.4.
- Removido botão Configurações da sidebar.
- Topo simplificado para logo + nome do projeto.
- Mantidos blocos estruturais de responsividade.
- Backend sem alteração funcional.


---

## V5.1.9 — Topo e Histórico limpos

- Removido botão Histórico da sidebar.
- Removida duplicação de logo/nome na barra interna.
- Mantido topo principal com logo + PedroCore IA.
- Preservada responsividade da V5.1.6.


---

## V5.1.9 — Remoção definitiva dos ícones do topo interno

- Removidos os ícones reais do topo interno.
- Removidos `window-dots` e `window-actions`.
- Responsividade preservada.
