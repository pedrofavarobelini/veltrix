# PedroCore IA — Status Atual

Atualizado em: 05/07/2026

## Status oficial

Reformulação documental (`PEDROCORE-REPLAN-01`) concluída; MVP backend (`PEDROCORE-IMPLEMENT-01`, `02` e `03`) implementado e commitado; consolidação documental `PEDROCORE-FINALIZE-04` commitada em `ee2ac68`; tag anotada `v6.0.0` criada apontando para `ee2ac68`. Este é o único documento de status oficial do projeto; prevalece sobre qualquer status antigo/duplicado ainda presente em `docs/`.

## Versão atual de produto

V5.1.9

## Frente atual

PEDROCORE-IMPLEMENT-04 — Expansão operacional segura (Blocos 8–11): contrato FinGuard fake, Artifact Reader allowlisted, QA visual stub e agente exploratório assistido. A tag `v6.0.0` (MVP backend) permanece intocada em `ee2ac68`.

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
- Endpoints `/`, `/health`, `POST /api/chat`, `GET /api/providers`.
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

## Em andamento

- `PEDROCORE-IMPLEMENT-04` — Expansão operacional segura (Blocos 8–11): contrato FinGuard → PedroCore por payload fake (`finguard`/`finguard-local`, `docs/11-integracoes/CONTRATO_FINGUARD_PEDROCORE.md`); Artifact Reader real controlado por allowlist (`apps/api/app/modules/artifact_reader/`, **desabilitado por padrão**, nunca para FinGuard, nunca `.env`/binário/segredo/traversal); QA visual stub (`visual_qa_analysis` conservador, sem OCR/provider multimodal/Playwright); agente exploratório assistido (`exploration` com `can_execute_actions=false` sempre). Testes backend: `166 passed, 2 warnings`. Implementada e validada localmente nesta frente.

## Ainda não existe

- Artifact Reader em uso real — o módulo existe mas fica **desabilitado por padrão** (`PEDROCORE_ARTIFACT_READER_ENABLED=false`); sem allowlist configurada, path em payload continua rejeitado (`ARTIFACT_PATH_REJECTED`); leitura de caminhos do FinGuard é bloqueada em qualquer configuração.
- QA Intelligence com IA real — a análise QA atual é heurística textual local determinística (`local_text_heuristic`); não usa provider real, não substitui validação humana e não executa testes.
- Execução de comandos pelo PedroCore — `suggested_commands` são apenas strings seguras, nada é executado; o agente exploratório é assistido (plano/manual) e nunca executa ações.
- QA visual real / OCR / Playwright — artefatos visuais geram apenas stub conservador com exigência de revisão humana (`ocr_attempted=false`, `provider_attempted=false`, `playwright_attempted=false`).
- Integração real executando no FinGuard — o contrato existe do lado do PedroCore com payload fake; o cliente HTTP no repositório do FinGuard é frente separada; nenhuma leitura de repositório/pasta do FinGuard existe.
- Provider real liberado em fluxo crítico — safe mode bloqueia por padrão; liberação exige `allow_real_provider=true` explícito e ainda assim mock/fallback nunca aprovam release gate.
- Bloqueio duro por policy de `allowed_tasks` — `task_allowed_for_project=False` apenas sinaliza.
- Provider Orchestration avançada (seleção por task_type/custo/qualidade).
- Persistência em banco de dados / log persistente (audit é não persistente, devolvido só na resposta). Dashboard (Bloco 12): **cancelado por decisão de produto**, não é pendência.
- Qualquer mudança de frontend/design — preservados sem alteração.
- Blocos 13–15 finais (documentação final, testes finais completos, fechamento Git/tag futuro).

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
- **`GEMINI_API_KEY` configurada localmente:** o `.env` real do backend tem a chave do Gemini preenchida; qualquer execução do servidor com `provider=gemini` gera uma chamada real. Isso não foi alterado e deve ser tratado com cuidado em qualquer teste manual futuro.
- **Fallback Mock silencioso:** o fallback automático para `MockProvider` evita quebrar a interface, mas pode mascarar falhas reais de provider se o consumidor não checar explicitamente o campo `fallback_used` — especialmente relevante para futuros consumidores externos e para qualquer caso de uso de QA (ver Decisão Técnica 014).
- **Resposta ainda não estruturada:** a API já aceita e sinaliza `task_type` e `task_criticality`, mas a resposta em si continua sendo texto livre (`answer: str`); `requires_structured_response` é apenas um indicador, sem validação de schema real, o que ainda limita o uso por sistemas externos que precisem consumir a resposta programaticamente.

## Próximos passos

- Validar e commitar `PEDROCORE-IMPLEMENT-04` (Blocos 8–11), sem mover/recriar a tag `v6.0.0`.
- Bloco 13 — Documentação final; Bloco 14 — Testes finais completos; Bloco 15 — Fechamento Git/tag futuro.
- Integração real no repositório FinGuard (cliente HTTP consumindo o contrato) em frente separada.
- OCR real, QA visual real com provider multimodal e Playwright real em frentes futuras, com aprovação explícita.
- Planejar enforcement real da policy de `allowed_tasks` (hoje só sinaliza via warning, não bloqueia).
- Provider real em fluxo crítico somente com autorização explícita (`allow_real_provider=true`) e revisão específica.
- Saneamento de documentação duplicada/legada permanece como pendência futura, a ser tratada em frente específica (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`).
