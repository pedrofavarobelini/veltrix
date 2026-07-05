# PedroCore IA — Decisões Técnicas

## Decisão 001 — Não treinar IA do zero

O projeto cria uma camada/orquestrador de IA, não um modelo próprio.

## Decisão 002 — Backend em Python

Python foi mantido por alinhamento com IA e aprendizado do usuário.

## Decisão 003 — Frontend em React + TypeScript

A interface continua simples, moderna e fácil de testar.

## Decisão 004 — V2 não será Gemini-only

A V2 entrega estrutura multi-provider completa inicial.

## Decisão 005 — Fallback obrigatório

Se qualquer provider real falhar, a resposta cai para MockProvider. Isso evita quebrar a interface.

## Decisão 006 — Chaves fora do código

Todas as API keys ficam somente no `.env`, nunca no GitHub ou no frontend.

## Decisão 007 — PedroCore IA como orquestrador central de IA do ecossistema Pedro

O PedroCore deixa de ser documentado apenas como chat pessoal e passa a ser a camada central de orquestração de IA para os projetos do ecossistema Pedro: recebe mensagem/contexto/tipo de tarefa, escolhe estratégia, seleciona provider/modelo e devolve resposta padronizada.

## Decisão 008 — Sistemas externos devem consumir IA preferencialmente via PedroCore

A direção estratégica é que outros sistemas do ecossistema Pedro consumam capacidades de IA através do PedroCore, em vez de integrarem provedores diretamente. Essa integração ainda não está implementada; é objetivo futuro.

## Decisão 009 — FinGuard é projeto externo e não deve ser alterado pelo PedroCore

O FinGuard permanece um repositório e sistema independentes. O PedroCore não altera código, dados, configuração ou documentação do FinGuard.

## Decisão 010 — QA Automation do FinGuard permanece dentro do FinGuard

A validação técnica (API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências) é e continua sendo um subsistema interno do FinGuard. O PedroCore não reimplementa nem substitui essa validação.

## Decisão 011 — IA exploratória/visual do QA será caso de uso futuro do PedroCore

Apenas a parte de IA exploratória/visual/inteligente do QA Automation do FinGuard foi delegada ao PedroCore, como caso de uso futuro (QA Intelligence). Não implementado nesta etapa.

## Decisão 012 — PedroCore não calcula números financeiros oficiais de sistemas externos

O PedroCore pode, no futuro, explicar, resumir e sugerir a partir de artefatos e dados lidos, mas nunca substitui os cálculos financeiros oficiais de sistemas como o FinGuard.

## Decisão 013 — Providers reais exigem controle explícito para evitar chamadas acidentais

A ausência de chave de API não pode ser o único mecanismo de proteção contra chamadas reais acidentais. Providers reais devem ter, no planejamento técnico futuro, um controle explícito (ex.: flag de ambiente ou confirmação) antes de serem acionados, especialmente em fluxos automatizados ou testes.

## Decisão 014 — Fallback Mock não pode validar tarefas críticas silenciosamente

O fallback automático para `MockProvider` é aceitável para preservar a experiência de chat, mas não pode ser usado, no futuro, para "validar" silenciosamente tarefas críticas de sistemas externos (ex.: análises de QA). Qualquer consumidor crítico deve checar explicitamente `fallback_used` antes de considerar uma resposta como real.

## Decisão 015 — Frontend/design ficam congelados durante a reformulação arquitetural

Durante a frente `PEDROCORE-REPLAN-01` (consolidação documental, planejamento técnico e arquitetura-alvo), nenhuma mudança de frontend, layout, tema, identidade visual ou componente é realizada. O frontend permanece na V5.1.9 até que a reformulação documental/arquitetural seja concluída.

## Decisão 016 — Contratos técnicos devem ser documentados antes da implementação

Qualquer contrato de entrada/saída, tipo de tarefa ou resposta estruturada do PedroCore deve ser especificado em documentação (`docs/10-contratos/`) antes de virar código. Isso reduz retrabalho e garante que decisões de segurança e escopo (ex.: limites com o FinGuard) sejam fixadas antes da implementação.

## Decisão 017 — Sistemas externos devem enviar `origin_system` e `task_type` em contratos futuros

Todo contrato futuro de orquestração exige, no mínimo, `origin_system` (quem está chamando) e `task_type` (o que está sendo pedido), para permitir roteamento, auditoria e aplicação de regras específicas por tipo de tarefa.

## Decisão 018 — Respostas críticas devem ter formato estruturado

Tarefas classificadas como críticas (ex.: `qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `visual_qa_analysis`) devem exigir `response_format: "structured"`, nunca apenas texto livre, para permitir que o sistema de origem processe a resposta de forma confiável.

## Decisão 019 — Artefatos externos devem ser recebidos inicialmente por payload, não por leitura automática de pastas

Nesta fase de planejamento, qualquer artefato (relatório, log, documento) só é considerado recebido pelo PedroCore se enviado no corpo da requisição (`artifacts[].content`). Leitura automática de diretórios ou arquivos de outros projetos (incluindo o FinGuard) é explicitamente fora de escopo até uma decisão arquitetural futura e específica.

## Decisão 020 — Tarefas críticas não podem depender silenciosamente de fallback Mock

Para tarefas críticas, uma resposta gerada via fallback (`MockProvider`) nunca deve ser apresentada como análise real. `fallback_used: true` nessas tarefas deve gerar warning forte e, dependendo do desenho futuro, bloquear a conclusão da tarefa (`status: "blocked"`), em vez de devolver um resultado simulado como se fosse confiável.

## Decisão 021 — QA Intelligence será planejada como caso de uso do PedroCore, não como substituição do QA Automation

A futura QA Intelligence do PedroCore (delegada de `QA-AUTOMATION-01G`) é um caso de uso de análise exploratória/visual assistida por IA, complementar ao QA Automation do FinGuard — nunca uma substituição da validação técnica (API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E) que continua sendo responsabilidade do próprio FinGuard.

## Decisão 022 — Task Router será responsável por classificar tarefas antes de chamar providers

Toda solicitação de orquestração deve ser classificada por `task_type`/`origin_system` antes de qualquer chamada a provider. O Task Router é o módulo planejado para essa responsabilidade; providers não devem decidir estratégia de tarefa.

## Decisão 023 — Prompt Builder será responsável por montar prompts; providers apenas executam chamadas

A montagem do prompt final (combinando `system_prompt`, `task_type`, contexto de projeto, artefatos e formato de resposta esperado) é responsabilidade do Prompt Builder planejado, não dos providers individuais. Providers executam a chamada ao modelo com o prompt já pronto.

## Decisão 024 — Project Context será a camada conceitual de configuração por sistema externo

Cada sistema externo (ex.: FinGuard) é representado, na arquitetura-alvo, por um Project Context com metadados e limites próprios (tarefas permitidas, somente leitura, proibição de executar comandos ou escrever arquivos), sem acoplamento direto ao código do sistema externo.

## Decisão 025 — `/api/chat` deve permanecer compatível durante a evolução arquitetural

Qualquer novo endpoint de orquestração deve coexistir com `POST /api/chat`, sem quebrar o uso conversacional atual nem exigir mudança no frontend existente.

## Decisão 026 — Artifact Reader futuro deve ser somente leitura e não pode executar comandos em projetos externos

Quando implementado, o Artifact Reader nunca escreve, nunca comita e nunca executa comandos em projetos externos (incluindo o FinGuard). Nesta fase, artefatos só são recebidos via payload, nunca por leitura automática de pasta/repositório.

## Decisão 027 — Audit/logs devem ser planejados antes de integrações reais com sistemas externos

Os campos de auditoria (origem, tarefa, provider, fallback, erro, latência, timestamp, criticidade) devem estar definidos e implementados antes de qualquer integração real com sistemas externos, para garantir rastreabilidade desde o primeiro uso em produção. Nenhum dado sensível ou chave de API deve ser armazenado em log.

## Decisão 028 — QA Intelligence será camada de análise, não executor de testes

QA Intelligence interpreta artefatos e relatórios já produzidos por processos de QA externos e devolve diagnóstico estruturado. Ela nunca executa testes, scripts, migrations, seed/reset ou qualquer comando dentro de um sistema externo, incluindo o FinGuard.

## Decisão 029 — Relatórios QA Markdown devem ser aceitos inicialmente como texto/payload

Como os relatórios de QA do FinGuard hoje são Markdown livre, o PedroCore deve planejar a extração de informações por interpretação textual tolerante a variação, sem depender inicialmente de um schema JSON estruturado do lado do sistema externo. JSON estruturado pode ser uma evolução futura, não um pré-requisito.

## Decisão 030 — Fallback Mock em tarefa crítica de QA deve bloquear ou reduzir confiança

Uma resposta de QA gerada via fallback (`MockProvider`) nunca pode ser tratada como análise real. Em tarefas críticas (`qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `visual_qa_analysis`), `fallback_used: true` deve resultar em `status: "warning"` ou `"blocked"` e `confidence` baixo, nunca em `can_advance: true`.

## Decisão 031 — `can_advance` é recomendação assistida, não autorização automática

A decisão de avançar uma frente de trabalho (ex.: para release) permanece sempre humana. O campo `can_advance` de QA Intelligence é uma sugestão baseada em evidências analisadas, nunca uma aprovação vinculante ou uma ação de release disparada automaticamente.

## Decisão 032 — Análise visual/exploratória deve ser planejada separadamente antes de qualquer automação

`visual_qa_analysis` e qualquer exploração visual autônoma (navegação, cliques, ações automáticas) dependem de uma fase própria de planejamento, posterior à maturação da base textual/estruturada de QA Intelligence. Nenhuma automação visual é implementada ou planejada em detalhe nesta etapa.

## Decisão 033 — QA Intelligence não pode alterar projetos externos nem aplicar correções automaticamente

QA Intelligence nunca altera arquivos, nunca faz commit, nunca aplica `suggested_fixes` automaticamente e nunca executa `suggested_commands`. Toda ação corretiva permanece de responsabilidade do sistema de origem ou de um humano.

## Decisão 034 — PEDROCORE-REPLAN-01 fecha apenas documentação e arquitetura, não implementação

O fechamento da frente `PEDROCORE-REPLAN-01` (etapa `01E`) consolida visão, contratos, arquitetura-alvo e planejamento de QA Intelligence em documentação. Nenhum código foi implementado durante toda a frente; a implementação é escopo de uma fase futura e separada.

## Decisão 035 — Documentação legada/duplicada não será removida sem frente específica de saneamento

Documentos antigos e duplicados identificados em `docs/` (ex.: pares `0X_NOME.md`/`0X-nome/`) permanecem no repositório após o fechamento de `PEDROCORE-REPLAN-01`. A remoção/consolidação desses documentos exige uma frente própria de saneamento documental, não incluída no escopo desta reformulação.

## Decisão 036 — Primeira implementação pós-replan deve preservar compatibilidade de `/api/chat`

Qualquer implementação futura decorrente desta reformulação (ex.: `PEDROCORE-IMPLEMENT-01`) deve manter `POST /api/chat` funcionando exatamente como hoje, sem exigir mudança no frontend existente.

## Decisão 037 — Implementação de Task Router deve ser incremental e testável com Mock antes de provider real

Ao implementar o Task Router, a primeira versão deve ser validável com `MockProvider`, permitindo testar o roteamento por `task_type` sem custo ou risco de chamada real, antes de habilitar providers reais nesse fluxo.

## Decisão 038 — Integração real com sistemas externos só deve ocorrer após contratos, autenticação e audit/log mínimos

Nenhuma integração real (ex.: recebendo chamadas do FinGuard) deve ser habilitada antes de existirem, no mínimo: o contrato de orquestração implementado, um mecanismo de autenticação entre sistemas e um audit/log básico registrando as chamadas.

## Decisão 039 — Task Router inicial deve começar como camada interna do /api/chat antes de novo endpoint público

A primeira implementação do Task Router deve operar dentro do fluxo já existente de `POST /api/chat`, preservando compatibilidade com clientes atuais e permitindo validação segura com Mock antes da criação de qualquer endpoint novo de orquestração.

## Decisão 040 — Warnings de fallback crítico devem ser expostos na resposta antes de qualquer bloqueio automático

Na primeira implementação, o fallback Mock em tarefa crítica não bloqueia a resposta — apenas adiciona um warning explícito em `task_warnings`. Bloqueio automático (ex.: `status: "blocked"`) é uma evolução futura, a ser decidida somente depois que sistemas externos reais consumirem e validarem esses warnings.

## Decisão 041 — Project Context mínimo deve ser configuração interna, não integração real com projetos externos

O Project Context resolve metadados e limites (`read_only`, `can_execute_commands`, `can_write_files`, `allowed_tasks`) a partir de configuração interna do próprio PedroCore, por `origin_system`. Ele nunca lê arquivos externos, nunca acessa o FinGuard real e nunca executa comandos — é estritamente um mapa de configuração local.

## Decisão 042 — Prompt Builder deve enriquecer system_prompt sem reescrever providers

O Prompt Builder monta um `system_prompt` enriquecido (tarefa, origem, limites do projeto, contexto, metadata, regras de segurança) e o repassa ao provider como parâmetro já existente. Ele não chama provider, não decide provider e não exige reescrever `BaseAIProvider` ou os providers individuais.

## Decisão 043 — Audit inicial deve ser não persistente até existir política de armazenamento e privacidade

O audit metadata (`audit_id`, `timestamp`, `origin_system`, `task_type`, `provider_requested`, `fallback_used`, `criticality`) é gerado em memória e devolvido apenas na resposta. Nenhuma persistência em banco, arquivo ou log é criada até que existam decisões explícitas de retenção, privacidade e armazenamento seguro.

## Decisão 044 — Orchestration module deve ser adiado até haver necessidade real de endpoint ou reuso fora do /api/chat

Um módulo dedicado de orquestração (`apps/api/app/modules/orchestration/`) não deve ser criado enquanto `ChatService` for o único consumidor do pipeline (Task Router, Project Context, Prompt Builder, Provider, fallback, audit). Extrair esse módulo antes de existir um segundo consumidor real (ex.: um futuro endpoint `/api/orchestrate`) seria abstração prematura.

## Decisão 045 — Artifact payload inicial deve aceitar apenas conteúdo enviado, sem leitura automática de arquivos

O recebimento de artefatos (`ChatRequest.artifacts`) processa exclusivamente o conteúdo textual enviado no corpo da requisição. Nenhum caminho de arquivo é aceito como instrução de leitura, e nenhuma leitura automática de disco/repositório é realizada — inclusive para artefatos do FinGuard.

## Decisão 046 — QA skeleton deve representar ausência de análise real até QA Intelligence existir

Enquanto QA Intelligence real não for implementada, qualquer resposta estruturada de QA (`QAResponseSkeleton`) deve ter `status="not_analyzed"`, listas de achados vazias e `confidence=0.0`, deixando explícito ao consumidor que nenhuma análise de fato ocorreu.

## Decisão 047 — allowed_tasks deve começar como warning/policy, não bloqueio duro

A avaliação de `task_type` contra `allowed_tasks` do Project Context (`TaskPolicyResult`) sinaliza `task_allowed_for_project` e adiciona warnings, mas não impede a execução da tarefa nesta fase. Bloqueio duro é uma evolução futura, a ser decidida separadamente.

## Decisão 048 — Artefatos visuais devem ser aceitos apenas como metadado/warning até análise visual existir

Artefatos do tipo `screenshot`, `image` ou `playwright_trace` são aceitos no payload apenas para gerar um warning de "análise visual ainda não implementada" — seu conteúdo não é incluído no prompt nem analisado de nenhuma forma até que a capacidade de análise visual real seja implementada.

## Decisão 049 — can_advance nunca pode ser true em skeleton sem análise real

Enquanto o `QAResponseSkeleton` não refletir uma análise real (QA Intelligence real ainda não implementada), o campo `can_advance` deve ser sempre `False`, nunca `True` — mesmo em fallback, mesmo com artefatos presentes.

## Decisão 050 — /api/orchestrate criado no MVP com pipeline centralizado em OrchestrationService

Por decisão explícita do MVP backend, o endpoint `POST /api/orchestrate` foi criado (atualizando a postura das Decisões 039 e 044): o pipeline completo foi extraído para `OrchestrationService`, que agora é consumido por dois clientes reais — `/api/chat` (compatibilidade legada, sem API key) e `/api/orchestrate` (contrato operacional completo para sistemas externos). A condição da Decisão 044 (segundo consumidor real) foi atendida.

## Decisão 051 — Safe mode: provider real bloqueado por padrão (allow_real_provider=false)

Nenhum provider real (Gemini, OpenAI, Claude, DeepSeek, Grok) é chamado sem `allow_real_provider=true` explícito no payload. Ausente = `false`. O bloqueio não instancia chamada externa, aplica fallback Mock e registra `PROVIDER_REAL_BLOCKED`, `safe_mode_blocked=true`, `fallback_used=true`, preservando `provider_requested`/`provider_used`.

## Decisão 052 — QA textual real inicial é heurística local determinística, não IA

A primeira análise QA real (`qa_analysis`) usa padrões textuais determinísticos locais (sem rede, sem chave, sem provider real) sobre artefatos enviados por payload. O skeleton preenchido declara `analysis_source="local_text_heuristic"`; `confidence` nunca chega a 1.0; a análise não substitui validação humana.

## Decisão 053 — Release gate conservador: mock nunca aprova; decisão vem da análise local

`release_gate_review` só libera `can_advance=true` com evidência textual limpa (sucesso explícito, sem falha/erro, risco `low`, confiança ≥ 0.6), sem fallback Mock, sem safe mode block e sem provider mock como fonte da resposta — o caminho aprovável é o pseudo-provider local `local_qa`, cuja decisão vem exclusivamente do QA Text Analyzer. Qualquer bloqueio preenche `blocked_reason` e `RELEASE_GATE_BLOCKED`.

## Decisão 054 — Artifacts com limites duros e rejeição de path; leitura de arquivo por payload é proibida

Limites: 10 artefatos, 20.000 caracteres por artefato, 100.000 no total (excedente truncado/ignorado com warning). Metadata contendo campos de caminho (`path`, `file_path`, `absolute_path`, `relative_path`, `filesystem_path`, `local_path`, `directory`, `folder`, `glob`) causa rejeição do artefato (`ARTIFACT_PATH_REJECTED`) sem qualquer leitura de disco — não existe e não deve existir `open`/`read_text`/`listdir`/`glob` sobre dados vindos de payload.

## Decisão 055 — Contrato padronizado de warnings/errors, auth interna opcional e audit não persistente completo

Respostas expõem `warning_codes`, `warnings` com severidade (`info`/`warning`/`error`/`critical`), `error_code`, `blocked_reason` e `status`, mantendo `task_warnings` textual por compatibilidade. `/api/orchestrate` aceita autenticação interna opcional (`PEDROCORE_INTERNAL_API_KEY` + header `X-PedroCore-Api-Key`; sem chave configurada, modo dev/local com `INTERNAL_AUTH_NOT_CONFIGURED`); `/api/chat` permanece livre. O audit (`audit_id`, `timestamp`, `origin_system`, `task_type`, `provider_requested`, `provider_used`, `fallback_used`, `safe_mode_blocked`, `status`, `latency_ms`, `risk_level`, `can_advance`) permanece não persistente e nunca contém segredos ou conteúdo de artefatos.

## Decisão 056 — Integração FinGuard começa por contrato e payload fake, nunca pelo repositório real

A integração FinGuard → PedroCore (Bloco 8) é implementada exclusivamente do lado do PedroCore: `origin_system` `finguard`/`finguard-local` com Project Context read-only, policy própria e contrato documentado (`docs/11-integracoes/CONTRATO_FINGUARD_PEDROCORE.md`). Nenhum arquivo do FinGuard é lido, nenhum comando é executado nele e o Artifact Reader é indisponível para origem FinGuard — inclusive por bloqueio de qualquer caminho contendo "finguard". A integração real (cliente HTTP no FinGuard) é frente separada.

## Decisão 057 — Artifact Reader real só existe atrás de allowlist e desabilitado por padrão

O único módulo autorizado a ler disco é `apps/api/app/modules/artifact_reader/`, controlado por `PEDROCORE_ARTIFACT_READER_ENABLED` (default `false`) e `PEDROCORE_ARTIFACT_ALLOWED_DIRS`. Bloqueios inegociáveis: path traversal, `.env`, extensão fora da lista, binário, segredo identificável, arquivo acima do limite, total acima do limite e qualquer caminho do FinGuard. O reader nunca escreve, nunca deleta, nunca executa. Com o reader desabilitado, o comportamento pré-existente permanece: path em payload é rejeitado (`ARTIFACT_PATH_REJECTED`).

## Decisão 058 — QA visual nesta fase é stub por contrato, sem OCR/provider multimodal/Playwright

Artefatos visuais (`screenshot`, `image`, `pdf`, `playwright_trace`) geram `visual_qa_analysis` conservador (`status=not_analyzed`, `supported=false`, `mode=stub`, `requires_human_review=true`, `can_advance=false`) com `ocr_attempted=false`, `provider_attempted=false`, `playwright_attempted=false` explícitos. Release gate nunca é liberado apenas com evidência visual não analisada (`VISUAL_QA_BLOCKED_FOR_RELEASE_GATE`).

## Decisão 059 — Agente exploratório é assistido (plano/manual), nunca autônomo

As tasks `exploratory_test_plan`, `manual_exploration_report` e `assisted_exploration_review` geram plano/checklist determinístico local (`exploration`) com `can_execute_actions=false` sempre. O agente não abre navegador, não clica, não executa Playwright, não roda comandos, não altera dados e não aprova release; pedidos destrutivos geram `EXPLORATION_ACTION_BLOCKED`. Confirmação humana é obrigatória (`HUMAN_CONFIRMATION_REQUIRED`).

## Decisão 060 — Bloco 12 (dashboard/logs/admin) cancelado por decisão de produto

O Bloco 12 do planejamento maior foi cancelado e não deve ser implementado nem listado como pendência obrigatória. Audit permanece não persistente.

## Decisão 061 — Recursos reais são opt-in, desabilitados por padrão e skipados no pytest padrão

Todo recurso real (OCR, provider multimodal, Playwright, integração FinGuard real, provider real em teste) é controlado por flag de ambiente explícita com default `false` (`real_features/service.py`), aceita apenas com o valor literal `true`. Os testes reais correspondentes existem em `tests/test_real_optin.py` e são SKIPPED no pytest padrão; nunca devem virar testes padrão.

## Decisão 062 — Somente a análise local determinística pode aprovar release gate

`RELEASE_GATE_TRUSTED_PROVIDERS = {"local_qa"}`: provider real/externo nunca aprova release gate sozinho, mesmo com `allow_real_provider=true` (`RELEASE_REQUIRES_HUMAN_REVIEW`); mock e fallback continuam bloqueados; evidência visual/OCR/exploração isolada nunca aprova. Revisão humana é obrigatória para qualquer decisão apoiada em recurso real (`PEDROCORE_RELEASE_REQUIRE_HUMAN_REVIEW_FOR_REAL_FEATURES=true` por padrão).

## Decisão 063 — Policy enforcement forte é o padrão; tasks perigosas têm bloqueio incondicional

`PEDROCORE_ENFORCE_PROJECT_POLICY=true` por padrão: task crítica não permitida para o projeto e origem desconhecida em fluxo crítico são bloqueadas de verdade (não chegam ao provider/reader/análise). task_type com semântica de execução/escrita/deleção/migração/deploy e payloads com chaves de comando são bloqueados incondicionalmente, mesmo com o enforcement desligado.

## Decisão 064 — Dependências pesadas (pytesseract, Playwright) nunca são instaladas automaticamente

OCR local e Playwright read-only foram implementados como guard + adapter: se a dependência não estiver instalada pelo humano, o resultado é bloqueio seguro (`OCR_DEPENDENCY_UNAVAILABLE`/`PLAYWRIGHT_DEPENDENCY_UNAVAILABLE`), nunca instalação automática nem falha de teste.

## Decisão 065 — v7.0.0 fecha o core operacional seguro local; integração no FinGuard é repositório separado

A tag `v7.0.0` marca o fechamento local do PedroCore IA como core operacional seguro (Blocos 1–11 + IMPLEMENT-05 + FINALIZE-06). O cliente HTTP no repositório do FinGuard, push/deploy e qualquer recurso real em produção são frentes futuras com aprovação própria. Bloco 12 (dashboard/admin) permanece cancelado (Decisão 060).
