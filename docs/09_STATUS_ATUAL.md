# PedroCore IA — Status Atual

Checkpoint documental atual: [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]] e [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]] consolidam as Etapas 1–7. Arquitetura multi-provider: concluída. Multi-provider automático operacional: não. Motivo: somente `gemini + gemini-3.5-flash` está homologado e elegível. Próximo passo: homologar um segundo provider real em frente separada.

Atualizado em: 26/07/2026

## Status oficial

Projeto finalizado localmente como core operacional seguro. `v7.0.0` é a tag final local e aponta para `33b2c0489c19776ef460fc85dea3c24298b46a3c`. `v6.0.0` permanece como tag do MVP backend e aponta para `ee2ac68679feea6ac108abba8726d11da101576c` (`ee2ac68`). Este é o documento de status oficial do projeto; prevalece sobre qualquer status antigo/duplicado ainda presente em `docs/`.

DOCFIX anterior: `docs/00_MAPEAMENTO_GERAL_PEDROCORE.md` e MOCs Obsidian em `docs/MOC_*.md` organizam a leitura atual sem alterar código.

Frente mais recente: Etapa 7 de
`PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`. O fallback real controlado existe
somente para falha `provider_pre_dispatch` com prova de `not_dispatched`; é
interno, default-off, limitado a `assistant_chat`/`ecosystem_assistant`, um
secundário distinto e dois registros de tentativa. Timeout continua como
conclusão ambígua e nunca dispara secundário. Como apenas
`gemini + gemini-3.5-flash` está homologado/autorizado no catálogo real, o
fallback multi-provider operacional permanece indisponível. Validação final é
`570 passed, 7 skipped, 2 warnings`, eval `14/14`, Ruff aprovado e zero
chamadas externas reais.

Correção anterior concluída:
`PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION — Fix — homologação e configuração
de modelos`, commit `8c97004`. `_MODEL_CATALOG` passou a ser a fonte explícita
dos modelos reconhecidos; configuração runtime apenas escolhe um identificador
e não cria/homologa entrada. Provider/model binding agora é total e falha
fechado antes de qualquer adapter real. Validação final registrada:
`515 passed, 7 skipped`, eval harness `14/14`, zero chamadas reais e
Gemini-only preservado.

### Estado consolidado da evolução multi-provider

| Etapa | Estado |
| --- | --- |
| Etapa 1 — catálogo de providers/modelos | concluída |
| Etapa 2 — identidade e autorização por projeto | concluída e corrigida |
| Etapa 3 — provider/model binding | concluída e corrigida |
| Etapa 4 — política determinística em shadow mode | concluída |
| Etapa 5 — roteamento enforced com chamada única | motor concluído; diversificação bloqueada por homologação |
| Etapa 6 — health/circuit breaker | concluída localmente; default-off e por processo |
| Etapa 7 — fallback real controlado | mecanismo pre-dispatch concluído; default-off e sem segundo homologado |

| Capacidade | Veredito atual |
| --- | --- |
| Multi-provider estrutural | sim |
| Identidade e autorização por projeto | sim |
| Provider/model binding total | sim |
| Shadow mode | sim |
| Multi-provider automático real | não |
| Health/circuit breaker | sim, local/default-off |
| Fallback entre providers reais | mecanismo pre-dispatch sim; operacional não |

O único candidato automático real permanece Gemini. Claude e OpenAI não são
executados automaticamente. Sem binding válido, `provider=auto` faz zero
chamadas reais e usa o Mock seguro; seleção técnica explícita é bloqueada com
zero adapters.

Frente anterior concluída: `PEDROCORE-OBSERVABILIDADE-LOCAL-01` — ring buffer sanitizado e default-off, painel `#/observability`, provider/fallback/timeline, relatórios, memória técnica, avaliação e release gate instrumentados no pipeline real. Integração local FinGuard → PedroCore → FinGuard e replay conjunto aprovados. Commits `b22338a`, `df6d72f`, `f995d5e`, `3b11b36`. Pytest: `368 passed, 7 skipped, 2 warnings`; frontend build verde. Gemini real não foi executado nesta frente porque os dois opt-ins permaneceram desligados. Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_OBSERVABILIDADE_LOCAL_01.md`.

Frente anterior: `PEDROCORE-MODEL-FOUNDATION-01` — fundação de inteligência própria, commitada em `689e50a`. Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01.md`.

Ultima frente de implementacao: `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` — pacote (A) contrato de ecossistema, (B) memória técnica controlada, (C) `local_model` opt-in sem rede, (D) eval harness determinístico; implementada de forma retrocompatível e commitada em `e0ff8e3`. O PedroCore continua **não** sendo modelo treinado: sem fine-tuning, sem autoaprendizado, sem RAG, sem provider real. Testes: `296 passed, 6 skipped, 2 warnings`. Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01.md`.

Ultima frente commitada: `PEDROCORE-QA-SAFETY-HARDENING-01` — endurecimento de QA/safety sem reabrir o core funcional, commitada em `d6106b7`. Pytest: `341 passed, 6 skipped, 2 warnings`. Eval harness: `14/14 passed`, `risk_level="none"`. Provider real e rede real nao foram chamados em testes; Report Memory continua default-off e nao e treinamento; `local_model` real ficou fora de escopo; FinGuard e `qa:finalize:02` ficaram intocados. Ver `docs/16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01.md`.

Frente documental anterior concluída: `PEDROCORE-DOCS-GRAPH-LINKING-01` — organização de links Markdown/Obsidian em `docs/`, sem alteração de código.

Frente local **validada com sucesso**: `FINGUARD-PEDROCORE-ASSISTANT-REAL-PROVIDER-QA-01`. O PedroCore decide `provider=auto` para consumidores externos: mock default, `local_qa` preservado, Gemini real somente com `allow_real_provider=true` e `GEMINI_API_KEY` no ambiente PedroCore. Corrigido bug de fallback que vazava texto tecnico/debug (`MockProvider`, `mock-v1`, erro bruto) na resposta conversacional — fallback agora sempre seguro/conservador (ver `docs/08_CHANGELOG.md`). Validacao manual confirmou Gemini real respondendo de forma conversacional via `provider=auto` (modelo `gemini-2.5-flash`; `gemini-3.5-flash`, o default de `.env`, estava com 503 transitorio do lado do Google no momento do teste). Teste real Gemini fica manual/opt-in e skipado por padrao. Pytest: `351 passed, 7 skipped, 2 warnings`.

## Versão atual de produto

V5.1.9

## Frente atual

Projeto **finalizado localmente** como core operacional seguro (`v7.0.0`). Últimas frentes: `PEDROCORE-IMPLEMENT-04` (Blocos 8–11, `18d1fc5`), `PEDROCORE-IMPLEMENT-05` (05A–05F: flags/guards opt-in, FinGuard controlado com policy forte, reader consolidado, OCR/multimodal/Playwright como opt-in seguro) e `PEDROCORE-FINALIZE-06` (06A enforcement final do release gate + 06B fechamento). A tag `v6.0.0` (MVP backend) permanece intocada em `ee2ac68`. Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md`.

`PEDROCORE-REPLAN-01` (01A a 01E) está **concluída no escopo documental** e commitada:

- `1e5a8cb — docs: iniciar PEDROCORE-REPLAN-01A`
- `6e7badd — docs: planejar contratos PEDROCORE-REPLAN-01B`
- `c1e7816 — docs: definir arquitetura-alvo PEDROCORE-REPLAN-01C`
- `8c68b67 — docs: planejar QA Intelligence PEDROCORE-REPLAN-01D`
- `cc808a7 — docs: fechar PEDROCORE-REPLAN-01E`

Implementação inicial de código:

- `PEDROCORE-IMPLEMENT-01A/01B` (Task Router mínimo + metadados de resposta) commitada em `577bc88`; correção documental commitada em `20e6cff`.
- `PEDROCORE-IMPLEMENT-01C/01D/01E/01F/01G/01H` (Project Context, Prompt Builder, metadados estruturais, audit não persistente) commitada em `95cbfab`; correção documental commitada em `1ff1758`.
- `PEDROCORE-IMPLEMENT-02A/02B/02C/02D/02E/02F/02G` — Policy de `allowed_tasks`, artefatos textuais por payload, Prompt Builder com artefatos, QA response skeleton seguro, warnings específicos de QA textual e testes de contrato — implementada, validada e commitada em `e115672`. Testes backend: `66 passed, 2 warnings`. `apps/web` limpo, `.env` intocado, nenhum provider real chamado, FinGuard não acessado, nenhum endpoint novo criado, QA skeleton sem análise real, `can_advance` nunca `true`.

## Local oficial

```txt
C:\Projetos\pedrocore-ia
```

## Concluído

- Backend FastAPI com estrutura multi-provider (`BaseAIProvider`, `ProviderRegistry`, 6 providers: Mock, Gemini, OpenAI, Claude, DeepSeek, Grok).
- Endpoints `/`, `/health`, `POST /api/chat`, `GET /api/providers`, `POST /api/orchestrate`.
- Fallback automático para `MockProvider` quando um provider real falha ou não está configurado.
- Frontend React/Vite/TypeScript com histórico local (`localStorage`), feedback gostei/não gostei, painel de configuração de providers e identidade visual aplicada (V5.1.9).
- Testes de backend cobrindo chat mock, fallback por provider desconhecido, validação de payload e listagem de providers.
- `PEDROCORE-REPLAN-01A` — visão oficial, objetivo, roadmap, status, decisões técnicas e changelog reformulados (commit `1e5a8cb`).
- `PEDROCORE-REPLAN-01B` — contratos técnicos planejados (`docs/10-contratos/`): contrato de orquestração, tipos de tarefa, resposta estruturada, contrato de artefatos, provider preference, fallback e relação com QA Intelligence (commit `6e7badd`).
- `PEDROCORE-REPLAN-01C` — arquitetura-alvo documentada (`docs/11-arquitetura-alvo/`): Task Router, Prompt Builder, Project Context, Provider Orchestration, Structured Responses, Artifact Reader, Audit/logs, relação com `/api/chat` e com o FinGuard (commit `c1e7816`).
- `PEDROCORE-REPLAN-01D` — planejamento de QA Intelligence documentado em `docs/12-qa-intelligence/` (definição, relação com o QA Automation do FinGuard, artefatos analisáveis, relatórios Markdown, casos de uso, resposta estruturada, severidade/risco, regra de avanço/bloqueio, fallback Mock, análise visual futura e limites/proibições) (commit `8c68b67`).
- `PEDROCORE-REPLAN-01E` — fechamento documental da reformulação, consolidado em `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md` (commit `cc808a7`).
- `PEDROCORE-IMPLEMENT-01A/01B` — Task Router mínimo implementado em código: `task_type`, `origin_system`, `context` e `metadata` opcionais no `ChatRequest`; Task Router mínimo em `apps/api/app/modules/task_router/` reconhecendo 7 task_types + `unknown`, sem bloqueio duro; metadados de tarefa (`task_type`, `origin_system`, `task_criticality`, `requires_structured_response`, `task_warnings`) no `ChatResponse`; warning forte quando fallback Mock ocorre em tarefa crítica. Commitada em `577bc88`.
- `PEDROCORE-IMPLEMENT-01C/01D/01E/01F/01G/01H` — Project Context mínimo (`apps/api/app/modules/project_context/`, resolve `pedrocore`/`finguard`/`unknown`, somente configuração interna); Prompt Builder mínimo (`apps/api/app/modules/prompt_builder/`, monta `enriched_system_prompt` sem chamar provider); metadados estruturais novos no `ChatResponse` (`project_id`, `project_read_only`, `project_can_execute_commands`, `project_can_write_files`, `response_style`, `audit_id`, `audit_timestamp`); audit metadata não persistente (`apps/api/app/modules/audit/`, `audit_id`/`timestamp` gerados em memória, sem banco/arquivo/log); testes backend: `37 passed, 2 warnings`. Commitada em `95cbfab`.
- `PEDROCORE-IMPLEMENT-02A/02B/02C/02D/02E/02F/02G` — QA textual foundation: policy de `allowed_tasks` (`ChatResponse.task_allowed_for_project`), artefatos textuais por payload (`apps/api/app/modules/artifacts/`, `ChatRequest.artifacts`, `ChatResponse.artifact_count`/`artifact_types`/`artifact_warnings`), Prompt Builder com seção `[Artefatos enviados]`, QA response skeleton seguro (`apps/api/app/modules/qa_response/`, `ChatResponse.qa_skeleton`, sempre `status="not_analyzed"`/`can_advance=False`/`confidence=0.0`, sem análise real), warnings específicos de QA textual e testes de contrato. Testes backend: `66 passed, 2 warnings`. Commitada em `e115672`.
- `PEDROCORE-IMPLEMENT-03` — MVP backend (Blocos 1–7): QA textual real inicial (heurística local determinística em `apps/api/app/modules/qa_analysis/`, skeleton preenchido com `analysis_source="local_text_heuristic"`), release gate conservador (`evaluate_release_gate` com `blocked_reason`), `POST /api/orchestrate` (pipeline centralizado em `apps/api/app/modules/orchestration/`, consumido também pelo `/api/chat`), safe mode (`allow_real_provider=false` por padrão, `PROVIDER_REAL_BLOCKED`), autenticação interna opcional (`PEDROCORE_INTERNAL_API_KEY` + `X-PedroCore-Api-Key`, somente `/api/orchestrate`), warning/error contract padronizado (`apps/api/app/modules/contracts/`) e audit não persistente completo (`latency_ms`, `provider_used`, `safe_mode_blocked`, `risk_level`, `can_advance`). Limites de artifacts (10 / 20k / 100k) e rejeição de campos de path sem leitura de disco. Testes backend: `125 passed, 2 warnings`. Commitada em `6ed4c41`.
- `PEDROCORE-FINALIZE-04` — consolidação documental do MVP backend, exemplos de API e preparação/registro da tag. Commitada em `ee2ac68`; tag anotada `v6.0.0` criada com a mensagem `v6.0.0 - MVP backend PedroCore IA`, apontando para `ee2ac68`.
- `PEDROCORE-IMPLEMENT-04` — expansão operacional segura (Blocos 8–11): contrato FinGuard por payload fake, Artifact Reader controlado, QA visual stub, agente exploratório assistido. Commitada em `18d1fc5`.
- `PEDROCORE-IMPLEMENT-05` — flags/guards/testes opt-in, FinGuard controlado com policy enforcement forte, reader consolidado, OCR local opt-in, multimodal guard e Playwright read-only opt-in. Commitada nas subfrentes `33a7dc2`, `790e1b4`, `70afba1`, `b3f1be5`, `2670040`, `3bcfa05`.
- `PEDROCORE-FINALIZE-06` — enforcement final do release gate, documentação final e tag local `v7.0.0`. HEAD esperado: `33b2c0489c19776ef460fc85dea3c24298b46a3c`.

- `PEDROCORE-MODEL-FOUNDATION-01` — fundação de inteligência própria: Intelligence Layer (`intelligence_layer/`, plano determinístico interno por task, nunca habilita provider real), Report Intelligence Foundation (`report_intelligence/`, sinais determinísticos de relatórios técnicos, sem persistência), contrato futuro do Local Model Provider (`providers/local_model_contract.py`, `local_model` ≠ `local_qa`, sem geração), Evaluation Foundation (`evaluation/`, checks de segurança/coerência) e 4 task_types novos somente para `pedrocore`. Testes backend: `257 passed, 6 skipped, 2 warnings` (41 novos). Commitada em `689e50a`.

- `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` — inteligência de ecossistema: contrato para consumidores + tasks de assistente (disclaimer obrigatório em `finance_advice`), memória técnica controlada (`report_memory/`, rotas `/api/reports/*` e `/api/project-memory/*`, default off, `context_from_memory` opt-in), provider `local_model` opt-in default-off (sem rede nesta frente; nunca aprova release gate) e eval harness determinístico (`eval_harness/`, 11 fixtures). Testes: `296 passed, 6 skipped, 2 warnings` (39 novos). Commitada em `e0ff8e3`.

- `PEDROCORE-QA-SAFETY-HARDENING-01` — guard estrutural contra provider real em testes, suites de safety para provider real/Report Memory/policy/contrato `/api/orchestrate`, eval harness estendido para 14 casos e docs de release gate em `docs/16-qa-safety-hardening/`. Testes: `341 passed, 6 skipped, 2 warnings`; eval harness `14/14 passed`, `risk_level="none"`. Commitada em `d6106b7`.

## Em andamento

Sem frente interna bloqueante aberta após `PEDROCORE-OBSERVABILIDADE-LOCAL-01`. Trabalhos futuros — provider real homologado, transport real do `local_model`, persistência operacional da observabilidade, push/deploy e execução real de OCR/multimodal/Playwright — são opcionais ou externos e exigem nova aprovação.

## Ainda não existe / permanece opcional

- Persistência operacional da observabilidade — o store atual é um ring buffer local/volátil e intencionalmente default-off.
- QA Intelligence com IA real — a análise QA atual é heurística textual local determinística (`local_text_heuristic`); não usa provider real, não substitui validação humana e não executa testes.
- Execução de comandos pelo PedroCore — `suggested_commands` são apenas strings seguras, nada é executado; o agente exploratório é assistido (plano/manual) e nunca executa ações.
- QA visual real multimodal — artefatos visuais geram stub conservador; OCR e Playwright existem como recursos opt-in/controlados, não como teste padrão nem release gate automático.
- Provider real liberado em fluxo crítico — safe mode bloqueia por padrão; liberação exige `allow_real_provider=true` explícito e ainda assim provider real nunca aprova release gate sozinho.
- Otimização dinâmica de provider por custo/qualidade/task; o roteamento determinístico shadow/enforced já existe.
- Memória técnica persistente por default e RAG — `report_memory` existe com persistência default off e modos opt-in (`memory`/`local_json`); RAG/embeddings ainda não existem.
- Provider generativo local funcional — `local_model` está registrado como provider opt-in default-off, mas sem transport real; nenhum backend (Ollama/llama.cpp/LM Studio) foi instalado ou chamado.
- Treinamento, fine-tuning ou autoaprendizado — fora do escopo do projeto; a fundação de inteligência é determinística e avaliada (`evaluation/`).
- Persistência em banco de dados / log persistente (audit e observabilidade permanecem voláteis). Dashboard público/admin (Bloco 12): **cancelado por decisão de produto**, não é pendência; o painel técnico local/QA foi implementado em `#/observability`.
- Qualquer mudança de frontend/design — preservados sem alteração.

## Proibido nesta fase

- Alterar `apps/web`, frontend, componentes, estilos, layout ou design.
- Instalar dependências ou rodar servidor.
- Chamar providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok) — inclusive em testes.
- Alterar `.env`.
- Ler, escrever ou executar comandos no repositório do FinGuard.
- Leitura de arquivo fora do Artifact Reader allowlisted (que permanece desabilitado por padrão e proibido para FinGuard).
- Implementar execução de comandos recebidos por payload.
- Remover documentação antiga/duplicada nesta etapa.
- Criar, mover, deletar ou recriar tag; alterar versão de produto/backend.

## Riscos atuais

- **Documentação duplicada:** ainda existem pares de arquivos conflitantes em `docs/` (ex.: `docs/03_ROADMAP.md` vs `docs/03-versoes/ROADMAP.md`, `docs/09-status/STATUS_ATUAL.md` desatualizado) que não foram removidos nesta etapa, apenas sinalizados.
- **Provider real autorizado explicitamente:** qualquer execução manual com provider real, chave/configuração disponível e `allow_real_provider=true` pode gerar chamada externa/custo. Testes padrão devem usar `mock` ou `local_qa`.
- **Fallback Mock silencioso:** o fallback automático para `MockProvider` evita quebrar a interface, mas pode mascarar falhas reais de provider se o consumidor não checar explicitamente o campo `fallback_used` — especialmente relevante para futuros consumidores externos e para qualquer caso de uso de QA (ver Decisão Técnica 014).
- **Structured response parcial:** `/api/orchestrate` já retorna `qa`, `release_gate`, `visual_qa_analysis`, `exploration`, `warnings` e `audit`, mas `answer` continua texto livre; otimização dinâmica por custo/qualidade/task ainda não existe.

## Próximos passos opcionais

- Cliente HTTP no repositório FinGuard (frente separada, com aprovação própria).
- Push para GitHub/portfólio e deploy.
- Execução real de OCR, QA visual multimodal e Playwright somente com flags, dependências instaladas manualmente e revisão humana.
- Homologar um segundo provider/modelo real em frente separada, escolhendo Claude ou OpenAI explicitamente; fluxo crítico continua exigindo autorização e revisão específica.
- Saneamento adicional de documentação histórica/duplicada, se o usuário quiser reduzir ruído do vault.
