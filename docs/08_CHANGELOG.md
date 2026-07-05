# PedroCore IA — Changelog

Atualizado em: 04/07/2026

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
