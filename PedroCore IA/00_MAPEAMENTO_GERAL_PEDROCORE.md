# Mapeamento Geral PedroCore IA

Atualizado em: 20/08/2026

> **Checkpoint canônico atual — Eras 1–3.** Era 1 (Operational Intelligence)
> PASS; Era 2 (Motor de Risco) PASS; Era 3 FOUNDATION PASS / TRAINING DEFERRED.
> Candidate Acquisition está implementada, mas há zero candidatos reais
> autorizados e `DATASET_NOT_READY`. Canonical Dataset, splits, Hugging Face,
> fine-tuning, modelo próprio e Local Provider treinado não existem neste
> checkpoint. Arquitetura consolidada e roadmap:
> [[19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]].

> As notas de checkpoint abaixo preservam fatos históricos de cada frente. Para
> números e estado corrente, prevalece o fechamento Eras 1–3: backend
> `924 passed, 7 skipped, 2 warnings`, Ruff global PASS e Pyright Era 3 sem
> erros.

> Nota MULTI-PROVIDER-SAFE-EVOLUTION: as Etapas 1–7 e as correções estão consolidadas em [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]] e [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]. Arquitetura multi-provider concluída; multi-provider automático operacional ainda não, pois somente `gemini + gemini-3.5-flash` está homologado e elegível. Última validação integral: `570 passed, 7 skipped, 2 warnings`; eval `14/14`, `risk_level="none"`; zero chamadas externas reais.

> Nota MODEL-FOUNDATION-01: a frente `PEDROCORE-MODEL-FOUNDATION-01` adicionou os módulos `intelligence_layer`, `report_intelligence`, `evaluation` e o contrato `providers/local_model_contract.py`, além de 4 task_types novos para `pedrocore`. Ver [[14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]] e [[13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01]].

> Nota ECOSYSTEM-INTELLIGENCE-SUITE-01: adicionou os módulos `report_memory` e `eval_harness`, o provider `local_model` opt-in (default OFF, sem rede nesta frente), 7 task_types de assistente/ecossistema, as rotas `POST /api/reports/analyze`, `POST /api/reports/ingest` e `GET /api/project-memory/{project_id}/summary`, os campos de request `allow_local_model`/`context_from_memory` (default false) e o campo de resposta `memory_used`. Testes da frente: `296 passed, 6 skipped, 2 warnings`. Ver [[13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01]], [[10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT]] e [[10-contratos/CONTRATO_REPORT_MEMORY]].

> Nota QA-SAFETY-HARDENING-01: a frente `PEDROCORE-QA-SAFETY-HARDENING-01`, commitada em `d6106b7`, endureceu QA/safety sem reabrir o core funcional. Resultado validado: `341 passed, 6 skipped, 2 warnings`; eval harness `14/14 passed`, `risk_level="none"`. Provider real e rede real nao foram chamados em testes; Report Memory continua default-off e nao e treinamento; `local_model` real e FinGuard seguem fora de escopo. Ver [[MOC_QA_SAFETY_HARDENING]] e [[16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]].

Links centrais: [[MOC_PEDROCORE_IA]] | [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]] | [[MOC_ARQUITETURA]] | [[MOC_SEGURANCA]] | [[MOC_QA_RELEASE_GATE]] | [[MOC_QA_SAFETY_HARDENING]] | [[MOC_INTEGRACOES]] | [[MOC_TESTES]] | [[MOC_VERSOES_STATUS]] | [[MOC_ESTUDO_PEDROCORE]]

## 1. Visao geral

O PedroCore IA esta finalizado localmente como core operacional seguro. O estado tecnico local verificado nesta tarefa e:

- Branch: `main`.
- Base de implementação desta consolidação: `e389b2cd8b7c04aacaa895303320a0b278ea4d26` (`e389b2c`).
- Último commit técnico da série: Etapa 7, fallback real controlado.
- Tag final local `v7.0.0`: aponta para `33b2c0489c19776ef460fc85dea3c24298b46a3c`.
- `v6.0.0`: tag do MVP backend, apontando para `ee2ac68679feea6ac108abba8726d11da101576c`.
- Working tree inicial: sem arquivos alterados no `git status --short`; o Git exibiu apenas warning de permissao ao ler `C:\Users\USUARIO/.config/git/ignore`.
- Push: nao realizado.
- Testes finais do core `v7.0.0`: `216 passed`, `6 skipped`, `2 warnings`.
- Testes integrais mais recentes: `570 passed`, `7 skipped`, `2 warnings`.
- Eval harness: `14/14 passed`, `risk_level="none"`.
- Ruff: aprovado; chamadas externas reais na validação: zero.
- Warnings conhecidos: deprecations Starlette/httpx e Pydantic class `Config`.

Este documento consolida o mapa atual do projeto sem alterar codigo de producao.

## 2. Objetivo do sistema

O PedroCore IA e a camada local de orquestracao de IA do ecossistema Pedro. Ele recebe uma mensagem, um tipo de tarefa, uma origem, contexto e artefatos textuais opcionais; aplica policy e limites de seguranca; decide a estrategia; chama um provider seguro ou pseudo-provider local; e devolve uma resposta padronizada com warnings, audit, QA textual e release gate quando aplicavel.

## 3. O que o PedroCore e

- API FastAPI local com frontend React/Vite preservado.
- Orquestrador de chat e tarefas operacionais.
- Camada de QA textual deterministica para artefatos enviados por payload.
- Release gate conservador baseado em evidencia textual local.
- Camada de seguranca para providers reais, Artifact Reader, OCR, Playwright, multimodal e integracao FinGuard.
- Sistema de audit nao persistente por resposta.

## 4. O que o PedroCore nao e

- Nao e agente autonomo destrutivo.
- Nao executa comandos enviados por payload.
- Nao escreve, deleta, migra, faz deploy, push, tag ou commit automaticamente.
- Nao acessa o repositorio FinGuard diretamente.
- Nao substitui validacao humana ou QA do sistema de origem.
- Nao calcula numeros financeiros oficiais do FinGuard.
- Nao usa provider real por padrao.

## 5. Arquitetura geral

Fluxo principal:

```text
FastAPI app/main.py
  GET /
  GET /health
  /api/chat         -> ChatService -> OrchestrationService
  /api/providers    -> ProviderRegistry
  /api/orchestrate  -> auth opcional -> OrchestrationService
  /api/reports/analyze            -> auth opcional -> ReportMemoryService (sem persistir)
  /api/reports/ingest             -> auth opcional -> ReportMemoryService (memoria opt-in)
  /api/project-memory/{id}/summary -> auth opcional -> ReportMemoryService

OrchestrationService
  Task Router
  Project Context
  Caller Identity
  Provider Catalog + Authorization + Binding
  Policy Enforcement
  Intelligence Layer (plano -> instrucoes do prompt)
  Report Memory opcional (context_from_memory=true)
  Artifact Reader opt-in
  Artifacts Service
  Prompt Builder
  Shadow Routing / Enforced Routing
  Provider Health / Circuit Breaker
  Provider Registry / local_qa / fallback Mock
  Fallback real pre-dispatch controlado
  QA Text Analyzer
  QA Response / Release Gate
  Visual QA stub
  Exploration assisted plan
  Audit non-persistent metadata
```

## 6. Endpoints

### `GET /`

- Onde: `apps/api/app/main.py`.
- Funcao: smoke simples da API.
- Resposta esperada: `status`, `service`, `version`, `message`.
- Quando usar: conferir se a API esta respondendo.
- Risco: baixo; nao chama provider.
- Teste local seguro:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:3333/" -Method GET
```

### `GET /health`

- Onde: `apps/api/app/main.py`.
- Funcao: healthcheck minimalista.
- Resposta esperada: `status="ok"`, `service="PedroCore IA"`, `version="0.2.0"`.
- Quando usar: smoke de ambiente local/API.
- Risco: baixo; nao chama provider.
- Teste local seguro:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:3333/health" -Method GET
```

### `POST /api/chat`

- Onde: `apps/api/app/modules/chat/router.py`.
- Funcao: endpoint legado/conversacional, preservado por compatibilidade.
- Implementacao: `ChatService` delega ao `OrchestrationService` e converte o resultado para `ChatResponse`.
- Payload minimo:

```json
{
  "message": "Explique o PedroCore IA em uma frase.",
  "provider": "mock",
  "mode": "tecnico"
}
```

- Resposta esperada: `answer`, `provider`, `model`, `requested_provider`, `fallback_used`, `status`, campos de tarefa/audit/QA com defaults seguros.
- Quando usar: chat local, frontend atual, compatibilidade com clientes antigos.
- Riscos: se solicitar provider real com `allow_real_provider=true`, pode chamar API externa se a chave estiver configurada. Teste padrao deve usar `mock` ou `local_qa`.
- Limite: nao exige API key interna.

### `GET /api/providers`

- Onde: `apps/api/app/modules/chat/router.py`.
- Funcao: listar providers registrados.
- Resposta esperada: lista com `name`, `label`, `default_model`, `configured`, `real_provider`.
- Providers registrados: `mock`, `gemini`, `openai`, `claude`, `deepseek`, `grok`.
- Quando usar: checar configuracao local visivel para o frontend.
- Risco: baixo; nao chama provider.
- Teste local seguro:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:3333/api/providers" -Method GET
```

### `POST /api/orchestrate`

- Onde: `apps/api/app/modules/orchestration/router.py`.
- Funcao: endpoint principal do core operacional.
- Auth: se `PEDROCORE_INTERNAL_API_KEY` estiver definido no ambiente, exige header `X-PedroCore-Api-Key`; se nao estiver, opera em modo dev/local com warning `INTERNAL_AUTH_NOT_CONFIGURED`.
- Payload minimo seguro:

```json
{
  "message": "Analise o relatorio textual.",
  "origin_system": "finguard",
  "task_type": "qa_report_analysis",
  "provider": "local_qa",
  "artifacts": [
    {
      "type": "qa_report",
      "name": "qa.txt",
      "content": "341 passed, 6 skipped, 2 warnings. Build successful. 0 failed."
    }
  ]
}
```

- Resposta esperada: `status`, `answer`, `warnings`, `warning_codes`, `error_code`, `blocked_reason`, `qa`, `release_gate`, `visual_qa_analysis`, `exploration`, `audit`.
- Quando usar: integracoes controladas, QA textual, release gate, payloads FinGuard.
- Riscos: provider real, path em artifact, task perigosa e origem desconhecida critica sao bloqueados ou sinalizados. Teste padrao deve usar `local_qa` ou `mock`.

## 7. Modulos

### `chat`

- Onde: `apps/api/app/modules/chat/`.
- O que faz: expoe `/api/chat` e `/api/providers`; mantem contrato legado.
- Conexao: delega chat para `OrchestrationService`; lista providers via `ProviderRegistry`.
- Status: finalizado e compatibilidade preservada.
- Default: on.
- Riscos controlados: safe mode e fallback tratados no pipeline central.
- Testes: `test_chat.py`, `test_orchestrate_api.py`, `test_safe_mode.py`, `test_finguard_enforcement.py`.

### `providers`

- Onde: `apps/api/app/modules/providers/`.
- O que faz: define `BaseAIProvider`, `ProviderRegistry`, `MockProvider` e providers reais estruturais.
- Conexao: usado pelo pipeline para obter provider solicitado; fallback usa `mock`.
- Status: finalizado para registry/fallback; providers reais dependem de chaves e autorizacao por request.
- Default: `mock`; providers reais default-off pelo safe mode.
- Riscos controlados: `allow_real_provider=false` bloqueia chamada real e gera `PROVIDER_REAL_BLOCKED`.
- Testes: `test_providers.py`, `test_safe_mode.py`, `test_real_optin.py`.

### `orchestration`

- Onde: `apps/api/app/modules/orchestration/`.
- O que faz: pipeline central do core.
- Conexao: consumido por `/api/chat` e `/api/orchestrate`.
- Status: endpoint principal finalizado.
- Default: on.
- Riscos controlados: policy hard block antes de provider/reader/QA; safe mode; release gate conservador.
- Testes: `test_orchestration_flow.py`, `test_orchestrate_api.py`, `test_release_hardening.py`.

### `caller_identity`

- Onde: `apps/api/app/modules/caller_identity/`.
- O que faz: resolve identidade confiável, papel, ambiente e projeto; credencial compartilhada não concede identidade privilegiada.
- Status: concluído e fail-closed.
- Testes: `test_caller_identity_authorization.py`, `test_shared_credential_privilege.py`.

### `provider_catalog`, `provider_authorization` e `provider_binding`

- Onde: `apps/api/app/modules/provider_catalog/`, `provider_authorization/` e `provider_binding/`.
- O que fazem: catalogam providers/modelos, aplicam autorização por identidade/projeto e exigem binding total antes do adapter.
- Status: concluídos; configuração runtime escolhe identificador, mas não cadastra nem homologa modelo.
- Testes: `test_provider_catalog.py`, `test_provider_model_binding.py`.

### `shadow_routing` e `provider_health`

- Onde: `apps/api/app/modules/shadow_routing/` e `provider_health/`.
- O que fazem: calculam candidatos/eliminações, aplicam roteamento determinístico e mantêm circuit breaker local por environment/provider/model.
- Status: shadow/enforced concluídos; circuit breaker local/default-off. Somente Gemini é elegível no catálogo real.
- Testes: `test_shadow_routing.py`, `test_routing_enforced.py`, `test_provider_health.py`, `test_real_provider_fallback.py`.

### `task_router`

- Onde: `apps/api/app/modules/task_router/`.
- O que faz: normaliza `task_type`, define criticidade, formato de resposta e se mock e permitido.
- Task types atuais: `general_chat`, `technical_explanation`, `code_help`, `qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `artifact_summary`, `exploratory_test_plan`, `manual_exploration_report`, `assisted_exploration_review`, `report_ingestion`, `project_memory_summary`, `model_foundation_review`, `intelligence_planning`, `assistant_chat`, `ecosystem_assistant`, `finance_advice`, `project_status`, `report_memory_query`, `local_model_chat`, `evaluation_run`, `unknown`. (Fundação de inteligência e maioria das tasks de ecossistema são de `pedrocore`; FinGuard recebe apenas `assistant_chat`/`finance_advice`/`project_status`/`report_memory_query` como consumidor read-only.)
- Status: finalizado para roteamento deterministico local.
- Default: `general_chat`.
- Riscos controlados: task desconhecida vira `unknown` com warning.
- Testes: `test_task_router.py`.

### `project_context`

- Onde: `apps/api/app/modules/project_context/`.
- O que faz: resolve `origin_system` para contexto interno e `allowed_tasks`.
- Origens reconhecidas: `pedrocore`, `finguard`, `finguard-local`, `unknown`.
- Status: finalizado para config em memoria.
- Default: `pedrocore`; `unknown` e restritivo em fluxos criticos.
- Riscos controlados: FinGuard sempre read-only; origem desconhecida critica e bloqueada por policy enforcement.
- Testes: `test_project_context.py`, `test_finguard_contract.py`, `test_finguard_enforcement.py`.

### `policy_enforcement`

- Onde: `apps/api/app/modules/policy_enforcement/`.
- O que faz: bloqueio forte para task perigosa, payload com comando, task critica nao permitida e origem desconhecida critica.
- Status: finalizado; default on via `PEDROCORE_ENFORCE_PROJECT_POLICY=true`.
- Default: on.
- Riscos controlados: provider, reader e QA nao executam quando `blocked=True`.
- Testes: `test_finguard_enforcement.py`, `test_release_hardening.py`.

### `prompt_builder`

- Onde: `apps/api/app/modules/prompt_builder/`.
- O que faz: monta prompt enriquecido com sistema, tarefa, origem, limites, contexto, metadata, artefatos e regras de seguranca.
- Status: finalizado para pipeline atual.
- Default: on.
- Riscos controlados: regras de nao executar comandos, nao alterar arquivos e tratar fallback/mock com cautela.
- Testes: `test_prompt_builder.py`.

### `artifacts`

- Onde: `apps/api/app/modules/artifacts/`.
- O que faz: processa artefatos enviados por payload, monta bloco textual, aplica limites e rejeita metadata de path.
- Limites: 10 artefatos; 20k caracteres por artefato; 100k caracteres totais.
- Status: finalizado para payload textual; visual apenas sinalizado/stub.
- Default: on.
- Riscos controlados: path rejeitado sem leitura; truncamento sinalizado.
- Testes: `test_artifacts.py`, `test_orchestrate_api.py`.

### `artifact_reader`

- Onde: `apps/api/app/modules/artifact_reader/`.
- O que faz: unico leitor de disco autorizado, apenas se habilitado e allowlisted.
- Status: implementado, opt-in e default-off.
- Default: off (`PEDROCORE_ARTIFACT_READER_ENABLED=false`).
- Riscos controlados: allowlist, extensoes, tamanho, total, path traversal, `.env`, binario, segredo, FinGuard bloqueado.
- Testes: `test_artifact_reader.py`, `test_finguard_contract.py`, `test_finguard_enforcement.py`.

### `qa_analysis`

- Onde: `apps/api/app/modules/qa_analysis/`.
- O que faz: heuristica textual local deterministica para tarefas QA criticas.
- Detecta: sucesso, falha, erro, warning, traceback/exception, lint/typecheck/build failed, producao, banco real, `drop table`, `truncate`, `delete from`, secret, token, senha, API key e `.env`.
- Status: finalizado como heuristica local; nao e IA real.
- Default: on para task critica com artefatos.
- Riscos controlados: nao le arquivo, nao executa comando, nao chama rede.
- Testes: `test_qa_analysis.py`, `test_qa_flow.py`.

### `qa_response`

- Onde: `apps/api/app/modules/qa_response/`.
- O que faz: cria `QAResponseSkeleton` e `ReleaseGateResult`.
- Status: finalizado para QA textual e release gate conservador.
- Default: on para tarefas QA.
- Riscos controlados: mock/fallback/safe mode/provider real nao aprovam release gate.
- Testes: `test_qa_response.py`, `test_release_gate.py`, `test_release_hardening.py`.

### `visual_qa`

- Onde: `apps/api/app/modules/visual_qa/`.
- O que faz: gera `visual_qa_analysis` conservador para screenshot/image/pdf/playwright_trace.
- Status: stub seguro; analise visual real nao executada.
- Default: on como stub quando artefato visual aparece.
- Riscos controlados: `requires_human_review=true`, `can_advance=false`, `ocr_attempted=false`, `provider_attempted=false`, `playwright_attempted=false`.
- Testes: `test_visual_qa.py`, `test_multimodal_guard.py`.

### `ocr`

- Onde: `apps/api/app/modules/ocr/`.
- O que faz: OCR local opt-in com `pytesseract/PIL` se flag e dependencia existirem.
- Status: opt-in; dependencia nao instalada pelo projeto; nao executa no teste padrao.
- Default: off (`PEDROCORE_OCR_ENABLED=false`).
- Riscos controlados: local-only, truncamento, segredo bloqueado, revisao humana.
- Testes: `test_ocr_guard.py`, `test_real_optin.py` skipado por padrao.

### `exploration`

- Onde: `apps/api/app/modules/exploration/`.
- O que faz: gera plano/checklist manual para exploracao assistida.
- Status: finalizado como plano local deterministico.
- Default: on para task exploratoria.
- Riscos controlados: `can_execute_actions=false`; nao abre navegador, nao clica, nao digita, nao executa comandos.
- Testes: `test_exploration.py`.

### `playwright_adapter`

- Onde: `apps/api/app/modules/exploration/playwright_adapter.py`.
- O que faz: adapter Playwright read-only opt-in.
- Status: opt-in; dependencia nao instalada pelo projeto; nao roda no pytest padrao.
- Default: off (`PEDROCORE_EXPLORATION_PLAYWRIGHT_ENABLED=false`).
- Riscos controlados: allowlist, FinGuard bloqueado, read-only, acoes interativas sempre bloqueadas.
- Testes: `test_playwright_guard.py`, `test_real_optin.py` skipado por padrao.

### `contracts`

- Onde: `apps/api/app/modules/contracts/`.
- O que faz: codigos padronizados de warnings/errors e severidades.
- Status: finalizado.
- Default: on.
- Riscos controlados: resposta estruturada permite consumidor detectar bloqueios e severidade.
- Testes: cobertos indiretamente por API/release/FinGuard.

### `audit`

- Onde: `apps/api/app/modules/audit/`.
- O que faz: gera `AuditMetadata` nao persistente por request.
- Status: finalizado sem banco/log persistente.
- Default: on.
- Riscos controlados: nao guarda conteudo de artefatos nem segredos.
- Testes: `test_orchestrate_api.py`.

### `intelligence_layer`

- Onde: `apps/api/app/modules/intelligence_layer/`.
- O que faz: gera `IntelligencePlan` determinístico (response_profile, política de contexto, safety flags, instruções) antes do provider.
- Status: fundação (`PEDROCORE-MODEL-FOUNDATION-01`); plano é metadado interno do `OrchestrationOutcome`, não exposto nos contratos públicos.
- Default: on (interno, sem efeito no contrato).
- Riscos controlados: nunca chama provider; `allow_real_provider=true` rejeitado por validação; nunca persiste memória.
- Testes: `test_intelligence_layer.py`.

### `report_intelligence`

- Onde: `apps/api/app/modules/report_intelligence/`.
- O que faz: normaliza relatórios técnicos por payload, extrai sinais determinísticos com severidade e agrega memória técnica volátil.
- Status: fundação; sem rota pública, sem persistência, sem RAG. Relatórios não treinam IA.
- Default: consumível internamente/por testes.
- Riscos controlados: sinais críticos exigem revisão humana; nenhum arquivo/repositório é lido.
- Testes: `test_report_intelligence.py`.

### `evaluation`

- Onde: `apps/api/app/modules/evaluation/`.
- O que faz: checks determinísticos de segurança/coerência para `IntelligencePlan` e sinais de relatório.
- Status: fundação; não é benchmark de LLM e não chama IA externa.
- Default: consumível internamente/por testes.
- Riscos controlados: reprova auto-training/fine-tuning/exposição de segredos; falha sempre exige revisão humana.
- Testes: `test_evaluation_foundation.py`.

### `report_memory`

- Onde: `apps/api/app/modules/report_memory/`.
- O que faz: memória técnica controlada — ingestão de relatórios por payload, sinais, snapshot por projeto e rotas `/api/reports/*` + `/api/project-memory/*`.
- Status: implementado (ECOSYSTEM-INTELLIGENCE-SUITE-01); relatórios não treinam IA.
- Default: off (`PEDROCORE_REPORT_MEMORY_PERSISTENCE=off`); `context_from_memory=false` por request.
- Riscos controlados: segredos redigidos, snapshot limitado (2k chars), isolamento por projeto, sem leitura de arquivo/repositório.
- Testes: `test_report_memory.py`.

### `eval_harness`

- Onde: `apps/api/app/modules/eval_harness/`.
- O que faz: harness determinístico de avaliação (14 fixtures após `PEDROCORE-QA-SAFETY-HARDENING-01`; executor `python -m app.modules.eval_harness.run`).
- Status: implementado; não é benchmark de LLM.
- Default: uso interno/testes; sem rota pública.
- Riscos controlados: `allow_real_provider=true` rejeitado por validação; sem rede.
- Testes: `test_eval_harness.py`.

### `providers/local_model_provider`

- Onde: `apps/api/app/modules/providers/local_model_provider.py`.
- O que faz: provider generativo local opt-in (`local_model`), registrado no registry como default OFF.
- Status: implementado sem transport real (fake transport em teste); nenhuma rede nesta frente.
- Default: off (`PEDROCORE_ENABLE_LOCAL_MODEL=false`, backend `disabled`); exige também `allow_local_model=true` por request.
- Riscos controlados: bloqueado em release gate/tarefa crítica; fora de `RELEASE_GATE_TRUSTED_PROVIDERS`; fallback Mock controlado; sem chave externa.
- Testes: `test_local_model_provider.py`.

### `providers/local_model_contract`

- Onde: `apps/api/app/modules/providers/local_model_contract.py`.
- O que faz: contrato do futuro provider generativo local (`local_model`), distinto do `local_qa`.
- Status: contrato de fundação; o provider registrado atual fica em `providers/local_model_provider`.
- Default: o contrato isolado não executa; pedir `local_model` passa pelo provider default-off e cai em fallback seguro quando falta opt-in, backend ou transport real.
- Riscos controlados: sem rede, sem backend, sem download de modelo.
- Testes: `test_local_model_contract.py`.

### `real_features`

- Onde: `apps/api/app/modules/real_features/`.
- O que faz: centraliza flags reais e defaults de seguranca.
- Status: finalizado.
- Default: recursos reais off; enforcement e revisao humana default true.
- Riscos controlados: opt-in estrito via string `true`.
- Testes: `test_real_feature_flags.py`, `test_real_optin.py`.

## 8. Fluxo `/api/orchestrate`

1. O router valida autenticação interna opcional e resolve `CallerIdentity`.
2. O payload usa o mesmo schema de `ChatRequest`.
3. `TaskRouter` normaliza `task_type`.
4. `ProjectContextResolver` resolve `origin_system`.
5. Catálogo, autorização e binding calculam os pares provider/modelo elegíveis.
6. Shadow routing registra candidatos/eliminações; `enforced` seleciona no máximo um binding inicial.
7. `PolicyEnforcementService` aplica bloqueio forte. Se bloquear, retorna `status="blocked"` sem provider, reader ou QA.
8. `_apply_artifact_reader` tenta converter path allowlisted em artefato textual apenas se reader habilitado e origem nao FinGuard.
9. `ArtifactService` processa artefatos por payload e aplica limites.
10. `PromptBuilder` monta prompt enriquecido.
11. Provider:
   - `local`/`local_qa`: pseudo-provider deterministico, sem rede.
   - `mock`: resposta simulada local.
   - provider real: somente com opt-in, identidade autorizada, binding válido e circuito elegível.
12. Falha comprovadamente pre-dispatch pode tentar um único secundário distinto se o fallback real estiver habilitado; timeout é ambíguo, afeta health e termina em Mock sem secundário.
13. `QATextAnalyzer` analisa artefatos textuais se task critica.
14. `QAResponseService` monta QA skeleton e release gate se aplicavel.
15. `VisualQAService` monta stub visual se houver artefato visual.
16. `ExplorationService` monta plano manual se task exploratoria.
17. Warnings sao coletados com codigos/severidades.
18. Audit registra identidade, seleção, tentativas, circuitos, dispatch, certeza, classificação, fallback, latência, risco e `can_advance`.

## 9. QA textual

O QA textual e uma heuristica local deterministica. Ele nao chama IA externa, nao le arquivos, nao executa comandos e nao substitui revisao humana.

Campos de saida em `qa`:

- `status`
- `summary`
- `findings`
- `failures`
- `probable_causes`
- `suggested_commands`
- `suggested_fixes`
- `risk_level`
- `can_advance`
- `confidence`
- `warnings`
- `analysis_source`
- `blocked_reason`

Padroes detectados:

- sucesso: `passed`, `success`, `build successful`, `0 failed`, `ok`, etc.
- falha: `failed`, `test failed`, `lint failed`, `typecheck failed`, `AssertionError`, etc.
- erro: `traceback`, `exception`, `SyntaxError`, `TypeError`, `ImportError`, `500 internal server error`, etc.
- warnings: `warning`, `deprecated`, `deprecationwarning`, etc.
- risco critico: producao, banco real, `drop table`, `truncate`, `delete from`, segredo, token, senha, API key, `.env`, provider real indevido, deploy.

## 10. Release gate

O release gate e conservador. Ele so aprova automaticamente quando todos os pontos abaixo sao verdadeiros:

- task `release_gate_review`;
- provider efetivo `local_qa`;
- evidencia textual limpa e processavel;
- risco `low`;
- confianca `>= 0.6`;
- sem fallback;
- sem safe mode bloqueando;
- sem path rejeitado;
- sem truncamento;
- sem falha ou erro detectado;
- sem provider real;
- sem evidencia apenas visual, OCR, Playwright ou exploration.

Bloqueios documentados:

- sem artifacts;
- artifact invalido ou path rejeitado;
- falha/erro;
- risco `high` ou `critical`;
- fallback mock;
- provider mock em release gate real;
- provider real sem revisao humana;
- visual-only;
- OCR-only;
- Playwright-only;
- exploration-only;
- task perigosa;
- policy bloqueada.

## 11. Policy enforcement

O enforcement forte bloqueia:

- `task_type` com semantica de executar, escrever, deletar, migrar, dar deploy, destruir, resetar ou rodar comando;
- chaves perigosas em `metadata` ou `context`, como `command`, `exec`, `shell`, `script`, `write_file`, `delete`;
- task critica nao permitida para o projeto;
- origem desconhecida em fluxo critico.

Quando bloqueia, `provider_used="none"` e a requisicao nao chega ao provider, Artifact Reader ou QA analyzer.

## 12. Providers

- `mock`: local, seguro, default/fallback.
- `local_qa`: pseudo-provider local deterministico para QA textual; nao chama rede.
- `local_model`: provider generativo local opt-in (ECOSYSTEM-INTELLIGENCE-SUITE-01) — default OFF, exige `allow_local_model=true` + `PEDROCORE_ENABLE_LOCAL_MODEL=true` + backend valido; sem transport real nesta frente (fallback controlado); nunca aprova release gate.
- `gemini`: `gemini-3.5-flash` homologado e autorizado para auto conforme identidade/policy.
- `claude`: `claude-sonnet-4-5` catalogado, não homologado e não autorizado para auto.
- `openai`: `gpt-5.2-mini` catalogado, não homologado e não autorizado para auto.
- `deepseek`: `deepseek-chat` catalogado, não homologado e não autorizado para auto.
- `grok`: `grok-4.3` catalogado, não homologado e não autorizado para auto.

Provider real é default-off. Mesmo autorizado, provider real não aprova release gate sozinho. Multi-provider automático real continua indisponível até a homologação de um segundo provider/modelo.

## 13. Safe mode

`allow_real_provider=false` e o default do schema. Se um provider real e solicitado sem autorizacao explicita, o pipeline:

- nao chama a API externa;
- marca `safe_mode_blocked=true`;
- gera warning `PROVIDER_REAL_BLOCKED`;
- usa fallback Mock;
- bloqueia release gate quando a tarefa e critica.

## 14. Artifact Reader

O Artifact Reader existe, mas e opt-in e default-off.

Condicoes para leitura:

- `PEDROCORE_ARTIFACT_READER_ENABLED=true`;
- `PEDROCORE_ARTIFACT_ALLOWED_DIRS` configurado;
- path resolvido dentro da allowlist;
- extensao permitida;
- arquivo texto UTF-8;
- dentro dos limites;
- sem segredo detectavel;
- nao `.env`;
- nao path traversal;
- nao binario;
- nao FinGuard.

Origem `finguard`/`finguard-local` nunca usa reader. Deve enviar conteudo por payload.

## 15. Visual QA

Visual QA atual e stub seguro. Artefatos visuais geram `visual_qa_analysis`, mas:

- `status="not_analyzed"`;
- `supported=false`;
- `mode="stub"`;
- `requires_human_review=true`;
- `can_advance=false`;
- `ocr_attempted=false`;
- `provider_attempted=false`;
- `playwright_attempted=false`.

## 16. OCR

OCR local e opt-in. Requer `PEDROCORE_OCR_ENABLED=true` e dependencias locais instaladas manualmente (`pytesseract`/`PIL`). Nao usa servico externo. Texto extraido exige revisao humana e nao libera release gate sozinho.

## 17. Playwright

Playwright read-only e opt-in. Requer `PEDROCORE_EXPLORATION_PLAYWRIGHT_ENABLED=true`, allowlist de base URLs e dependencia instalada manualmente. O adapter nao clica, nao digita, nao submete formularios, nao faz login e nao acessa FinGuard.

## 18. Exploration

Exploration e assistida/manual. O PedroCore gera plano, passos manuais, riscos, evidencias exigidas e confirmacoes humanas. `can_execute_actions` e sempre `false`.

## 19. Audit

Audit é não persistente. Inclui identidade/origem, provider/modelo solicitado e selecionado, modo de roteamento, shadow/candidatos, tentativas, circuitos, dispatch externo, certeza de conclusão, classificação de falha, fallback, latência, risco e `can_advance`. Não grava banco, arquivo ou log persistente; também não inclui conteúdo de artefatos ou segredos.

## 20. Integracao com FinGuard pelo lado PedroCore

O PedroCore reconhece:

- `origin_system="finguard"`;
- `origin_system="finguard-local"`.

Task types permitidos:

- `qa_report_analysis`;
- `qa_failure_diagnosis`;
- `release_gate_review`;
- `exploratory_test_plan`;
- `manual_exploration_report`;
- `assisted_exploration_review`;
- `artifact_summary`;
- `technical_explanation`.

Bloqueios obrigatorios:

- nao acessa repositorio FinGuard;
- nao le path real do FinGuard;
- Artifact Reader nao aponta para FinGuard por padrao e e bloqueado para origem/caminho FinGuard;
- comandos bloqueados;
- escrita/delecao/deploy bloqueados;
- provider real bloqueado por padrao;
- consumidor comum pede `provider=auto` sem modelo;
- credencial compartilhada nunca autoriza provider real;
- provider/modelo final é decidido pelo PedroCore;
- release gate conservador.

Documentos oficiais:

- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE]]
- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO]]

O cliente HTTP do Assistente no FinGuard já consome `/api/orchestrate`. Esta consolidação não altera o repositório FinGuard nem executa qualquer ação nele.

## 21. Como testar

### Bloco 1 - Verificar Git

```powershell
cd C:\Projetos\pedrocore-ia
git status --short
git branch --show-current
git rev-parse HEAD
git tag --points-at HEAD
```

### Bloco 2 - Instalar dependencias, se necessario

O projeto usa `uv` no backend. Documentado, nao execute sem necessidade:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
uv sync
```

### Bloco 3 - Subir API local

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 3333
```

Alternativa se usar `uv`:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
uv run uvicorn app.main:app --reload --port 3333
```

### Bloco 4 - Testar healthcheck

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:3333/health" -Method GET
```

### Bloco 5 - Testar providers

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:3333/api/providers" -Method GET
```

### Bloco 6 - Testar `/api/chat`

```powershell
$body = @{
  message = "Explique o PedroCore IA em uma frase."
  mode = "tecnico"
  provider = "mock"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:3333/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

### Bloco 7 - Testar `/api/orchestrate`

```powershell
$body = @{
  message = "Pode avancar para release?"
  origin_system = "finguard"
  task_type = "release_gate_review"
  provider = "local_qa"
  artifacts = @(
    @{
      type = "qa_report"
      name = "qa.txt"
      content = "341 passed, 6 skipped, 2 warnings. Build successful. 0 failed."
    }
  )
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Uri "http://127.0.0.1:3333/api/orchestrate" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

### Bloco 8 - Rodar suite de testes

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -q
```

Comando alternativo:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
uv run pytest -q
```

Resultado integral mais recente, após a Etapa 7: `570 passed, 7 skipped, 2 warnings`.

Eval harness:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m app.modules.eval_harness.run
```

Resultado integral mais recente: `14/14 passed`, `risk_level="none"`.

Testes que usem provider real, OCR real, multimodal real ou Playwright real sao opt-in e nao fazem parte do teste padrao. Exigem flags `PEDROCORE_RUN_REAL_*_TESTS=true`, dependencias/chaves reais e aprovacao humana.

## 22. Comandos uteis

```powershell
git diff --name-only
git diff --stat
git diff --check
```

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
.\.venv\Scripts\python.exe -m pytest -q tests/test_release_gate.py
```

## 23. Estado Git/versionamento

- `v7.0.0`: fechamento tecnico local do core operacional seguro.
- `d6106b7`: `PEDROCORE-QA-SAFETY-HARDENING-01`, endurecimento QA/safety sem reabrir core.
- `62beff1` a `e389b2c`: Etapas 1–7 e correções da evolução multi-provider segura.
- `v6.0.0`: MVP backend.
- Pendencia obrigatoria de codigo/teste/Git: zero no estado final registrado.
- Push/tag/merge: nao realizados nesta tarefa.

## 24. O que esta fechado

- Core backend operacional local.
- `/api/chat` legado.
- `/api/orchestrate` operacional.
- QA textual local.
- Release gate conservador.
- Safe mode.
- Policy enforcement forte.
- Contrato FinGuard pelo lado PedroCore.
- Artifact Reader opt-in.
- OCR/Playwright/multimodal como guards/opt-in.
- Testes padrao finais registrados.
- Tag local `v7.0.0`.
- QA Safety Hardening documentado e validado em `d6106b7`.
- Arquitetura multi-provider segura das Etapas 1–7, incluindo catálogo, identidade, binding, shadow/enforced, health e fallback pre-dispatch.

## 25. Pendencias obrigatorias

Após esta consolidação, não há pendência arquitetural nas Etapas 1–7. Há uma pendência operacional explícita: homologar um segundo provider/modelo real em frente separada. O repositório ainda pode manter documentos históricos/legados para contexto, que devem ser lidos pelos MOCs e por este mapeamento.

## 26. Melhorias opcionais

- Homologação de um segundo provider/modelo real, após escolha explícita entre Claude e OpenAI.
- Push para GitHub/portfolio.
- Deploy.
- Logs persistentes se a decisao de produto mudar.
- Otimização dinâmica de provider por custo/qualidade/task; o roteamento determinístico já existe.
- Execucao real de OCR/Playwright/multimodal com aprovacao, flags e dependencias.
- Saneamento mais agressivo de documentos historicos duplicados, sem apagar historico util.

## 27. Riscos e limites

- Heuristica QA textual pode ter falso positivo/falso negativo.
- Detecao de segredo por regex nao e exaustiva.
- Provider real pode gerar custo/chamada externa se autorizado explicitamente e configurado.
- Fallback Mock pode mascarar erro se consumidor ignorar `fallback_used`.
- Timeout de provider tem conclusão ambígua: não é cancelamento comprovado e nunca permite tentativa secundária. Desde [[18-provider-output-budget-cancellation/PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]] o adapter Gemini é assíncrono e fecha o transporte local, mas fechar a conexão continua não provando que a geração remota parou.
- Orçamento de saída (`min(global_cap, model_cap, task_cap)`) e timeout de transporte são decididos só pelo PedroCore; o consumidor não tem campo para influenciá-los. Os valores derivam do `response_style` das tasks, não de medição real de tokens.
- Fechamento do transporte distingue tentativa de confirmação (`transport_close_requested` e `transport_close_outcome`); `unknown` é o valor honesto quando o resultado não é observável. Nem mesmo `confirmed` prova término remoto. Ver [[18-provider-output-budget-cancellation/PEDROCORE_ASSISTANT_FINAL_CLOSURE_01]].
- Assistente IA do FinGuard: **encerrado** com homologação real **4/4**. O cenário `Organizar`, última limitação aberta, foi aprovado com Gemini real em [[19-encerramento-final/PEDROCORE_ENCERRAMENTO_FINAL_01]]. A leitura `3/4` pertence ao estado anterior a esse fechamento e permanece apenas nas seções históricas de [[03-versoes/ROADMAP]].
- Resposta com `finish_reason=MAX_TOKENS` é tratada como incompleta: texto parcial não é publicado, e não há continuação, retry nem segundo provider.
- Circuit breaker é local por processo, usa relógio monotônico e fica default-off; não substitui health distribuído.
- Fallback real é default-off e só aceita `provider_pre_dispatch + not_dispatched + external_dispatch=false`.
- Apenas um provider/modelo externo está homologado e elegível; a arquitetura não equivale a operação multi-provider.
- Artifact Reader e seguro por allowlist, mas deve permanecer default-off.
- OCR/Playwright/multimodal dependem de dependencias e revisao humana.
- Audit nao persistente nao substitui trilha operacional duravel.
- Documentos historicos ainda existem e podem conter contexto de fase antiga; use [[MOC_PEDROCORE_IA]] e este documento como entrada atual.
