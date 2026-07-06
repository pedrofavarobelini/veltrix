# Mapeamento Geral PedroCore IA

Atualizado em: 05/07/2026

Links centrais: [[MOC_PEDROCORE_IA]] | [[MOC_ARQUITETURA]] | [[MOC_SEGURANCA]] | [[MOC_QA_RELEASE_GATE]] | [[MOC_INTEGRACOES]] | [[MOC_TESTES]] | [[MOC_VERSOES_STATUS]]

## 1. Visao geral

O PedroCore IA esta finalizado localmente como core operacional seguro. O estado tecnico local verificado nesta tarefa e:

- Branch: `main`.
- HEAD: `33b2c0489c19776ef460fc85dea3c24298b46a3c`.
- Tag no HEAD: `v7.0.0`.
- `v6.0.0`: tag do MVP backend, apontando para `ee2ac68679feea6ac108abba8726d11da101576c`.
- Working tree inicial: sem arquivos alterados no `git status --short`; o Git exibiu apenas warning de permissao ao ler `C:\Users\USUARIO/.config/git/ignore`.
- Push: nao realizado.
- Testes finais ja registrados no fechamento: `216 passed`, `6 skipped`, `2 warnings`.
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

OrchestrationService
  Task Router
  Project Context
  Policy Enforcement
  Artifact Reader opt-in
  Artifacts Service
  Prompt Builder
  Provider Registry / local_qa / fallback Mock
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
      "content": "216 passed, 6 skipped, 2 warnings. Build successful. 0 failed."
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

### `task_router`

- Onde: `apps/api/app/modules/task_router/`.
- O que faz: normaliza `task_type`, define criticidade, formato de resposta e se mock e permitido.
- Task types atuais: `general_chat`, `technical_explanation`, `code_help`, `qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `artifact_summary`, `exploratory_test_plan`, `manual_exploration_report`, `assisted_exploration_review`, `unknown`.
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

### `real_features`

- Onde: `apps/api/app/modules/real_features/`.
- O que faz: centraliza flags reais e defaults de seguranca.
- Status: finalizado.
- Default: recursos reais off; enforcement e revisao humana default true.
- Riscos controlados: opt-in estrito via string `true`.
- Testes: `test_real_feature_flags.py`, `test_real_optin.py`.

## 8. Fluxo `/api/orchestrate`

1. O router valida auth interna opcional.
2. O payload usa o mesmo schema de `ChatRequest`.
3. `TaskRouter` normaliza `task_type`.
4. `ProjectContextResolver` resolve `origin_system`.
5. `PolicyEnforcementService` aplica bloqueio forte. Se bloquear, retorna `status="blocked"` sem provider, sem reader e sem QA.
6. `_apply_artifact_reader` tenta converter path allowlisted em artefato textual apenas se reader habilitado e origem nao FinGuard.
7. `ArtifactService` processa artefatos por payload e aplica limites.
8. `PromptBuilder` monta prompt enriquecido.
9. Provider:
   - `local`/`local_qa`: pseudo-provider deterministico, sem rede.
   - `mock`: resposta simulada local.
   - provider real: so se `allow_real_provider=true`; caso contrario safe mode bloqueia e cai para mock.
10. `QATextAnalyzer` analisa artefatos textuais se task critica.
11. `QAResponseService` monta QA skeleton e release gate se aplicavel.
12. `VisualQAService` monta stub visual se houver artefato visual.
13. `ExplorationService` monta plano manual se task exploratoria.
14. Warnings sao coletados com codigos/severidades.
15. Audit e completado com latencia, provider usado, status, risco e `can_advance`.

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
- `gemini`, `openai`, `claude`, `deepseek`, `grok`: providers reais estruturais; exigem chave/configuracao e `allow_real_provider=true`.

Provider real e default-off. Mesmo autorizado, provider real nao aprova release gate sozinho.

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

Audit e nao persistente. Ele inclui `audit_id`, `timestamp`, `origin_system`, `task_type`, `provider_requested`, `provider_used`, `fallback_used`, `safe_mode_blocked`, `status`, `latency_ms`, `risk_level` e `can_advance`. Nao grava banco, arquivo ou log persistente; tambem nao inclui conteudo de artefatos.

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
- release gate conservador.

Documentos oficiais:

- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE]]
- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO]]

O cliente HTTP dentro do FinGuard ainda e trabalho fora deste repositorio e exige aprovacao propria.

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
      content = "216 passed, 6 skipped, 2 warnings. Build successful. 0 failed."
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

## 25. Pendencias obrigatorias

Apos este DOCFIX, nao ha pendencia obrigatoria de codigo, teste, Git ou documentacao central conhecida dentro do escopo local. O repositorio ainda pode manter documentos historicos/legados para contexto, mas eles agora devem ser lidos atraves dos MOCs e deste mapeamento.

## 26. Melhorias opcionais

- Cliente HTTP no repositorio FinGuard.
- Push para GitHub/portfolio.
- Deploy.
- Logs persistentes se a decisao de produto mudar.
- Provider orchestration avancada por custo/qualidade/task.
- Execucao real de OCR/Playwright/multimodal com aprovacao, flags e dependencias.
- Saneamento mais agressivo de documentos historicos duplicados, sem apagar historico util.

## 27. Riscos e limites

- Heuristica QA textual pode ter falso positivo/falso negativo.
- Detecao de segredo por regex nao e exaustiva.
- Provider real pode gerar custo/chamada externa se autorizado explicitamente e configurado.
- Fallback Mock pode mascarar erro se consumidor ignorar `fallback_used`.
- Artifact Reader e seguro por allowlist, mas deve permanecer default-off.
- OCR/Playwright/multimodal dependem de dependencias e revisao humana.
- Audit nao persistente nao substitui trilha operacional duravel.
- Documentos historicos ainda existem e podem conter contexto de fase antiga; use [[MOC_PEDROCORE_IA]] e este documento como entrada atual.
