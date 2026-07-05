# PedroCore IA — Status Atual

Atualizado em: 04/07/2026

## Status oficial

Reformulação documental (`PEDROCORE-REPLAN-01`) concluída; implementação inicial de código em andamento (`PEDROCORE-IMPLEMENT-01`). Este é o único documento de status oficial do projeto; prevalece sobre qualquer status antigo/duplicado ainda presente em `docs/`.

## Versão atual de produto

V5.1.9

## Frente atual

PEDROCORE-IMPLEMENT-02A/02B/02C/02D/02E/02F/02G — QA textual foundation.

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

## Em andamento

Nenhuma frente em andamento no momento — `PEDROCORE-IMPLEMENT-02A/02B/02C/02D/02E/02F/02G` está implementada, validada e commitada em `e115672`.

## Ainda não existe

- Artifact Reader real — artefatos só são recebidos via payload; nenhuma leitura automática de arquivo/pasta foi implementada.
- QA Intelligence real — o QA response skeleton sinaliza estrutura (`status`, `risk_level`, `findings`, etc.), mas não há parser de relatório, classificador de risco ou lógica de diagnóstico real; nenhum `finding`/`failure` é inferido.
- Endpoint `/api/orchestrate` ou qualquer endpoint novo de orquestração — o pipeline opera internamente dentro de `POST /api/chat` (Decisão Técnica 039).
- Orchestration module (`apps/api/app/modules/orchestration/`) — avaliado na etapa `01I` e adiado; `ChatService` já encapsula o pipeline, extrair um módulo agora seria abstração prematura.
- Resposta estruturada real por tipo de tarefa (o `ChatResponse` sinaliza `requires_structured_response` e devolve `qa_skeleton`, mas a resposta em si continua sendo `answer: str` livre; o skeleton é sempre vazio/conservador).
- Bloqueio duro por policy de `allowed_tasks` — `task_allowed_for_project=False` apenas sinaliza, não impede a execução da tarefa.
- Análise visual real — artefatos visuais (`screenshot`, `image`, `playwright_trace`) só geram warning de "não suportado", nunca são analisados.
- Provider Orchestration avançada (seleção por task_type/custo/qualidade) — a seleção de provider continua manual/por default.
- Leitura real de arquivos do FinGuard — nenhuma leitura automática de repositório ou pasta do FinGuard existe; Project Context é apenas configuração interna.
- Persistência em banco de dados (histórico hoje só existe no navegador; audit metadata é não persistente).
- Autenticação entre sistemas externos e o PedroCore.
- Qualquer integração real com o FinGuard ou outro sistema externo.
- Qualquer mudança de frontend/design — preservados sem alteração.

## Proibido nesta fase

- Alterar `apps/web`, frontend, componentes, estilos, layout ou design.
- Instalar dependências ou rodar servidor.
- Chamar providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok).
- Alterar `.env`.
- Ler, escrever ou executar comandos no repositório do FinGuard.
- Criar endpoint `/api/orchestrate` ou qualquer endpoint novo de orquestração.
- Implementar Prompt Builder real, Project Context real, Artifact Reader, QA Intelligence real ou Audit/logs.
- Remover documentação antiga/duplicada nesta etapa.
- Criar tag ou alterar versão de produto/backend.

## Riscos atuais

- **Documentação duplicada:** ainda existem pares de arquivos conflitantes em `docs/` (ex.: `docs/03_ROADMAP.md` vs `docs/03-versoes/ROADMAP.md`, `docs/09-status/STATUS_ATUAL.md` desatualizado) que não foram removidos nesta etapa, apenas sinalizados.
- **`GEMINI_API_KEY` configurada localmente:** o `.env` real do backend tem a chave do Gemini preenchida; qualquer execução do servidor com `provider=gemini` gera uma chamada real. Isso não foi alterado e deve ser tratado com cuidado em qualquer teste manual futuro.
- **Fallback Mock silencioso:** o fallback automático para `MockProvider` evita quebrar a interface, mas pode mascarar falhas reais de provider se o consumidor não checar explicitamente o campo `fallback_used` — especialmente relevante para futuros consumidores externos e para qualquer caso de uso de QA (ver Decisão Técnica 014).
- **Resposta ainda não estruturada:** a API já aceita e sinaliza `task_type` e `task_criticality`, mas a resposta em si continua sendo texto livre (`answer: str`); `requires_structured_response` é apenas um indicador, sem validação de schema real, o que ainda limita o uso por sistemas externos que precisem consumir a resposta programaticamente.

## Próximos passos

- Planejar a próxima etapa de `PEDROCORE-IMPLEMENT-02` ou abrir `PEDROCORE-IMPLEMENT-03`.
- Avaliar limite de tamanho de artefatos (`ArtifactService`) antes de qualquer uso com provider real.
- Planejar enforcement real da policy de `allowed_tasks` (hoje só sinaliza via warning, não bloqueia).
- Planejar QA Intelligence textual real (parser de relatório, classificador de risco) para preencher o skeleton com achados reais, consumindo os artefatos textuais já recebidos.
- Manter Artifact Reader real, análise visual real, endpoint `/api/orchestrate` e integração real com o FinGuard como não implementados até decisão explícita em etapa futura.
- Saneamento de documentação duplicada/legada permanece como pendência futura, a ser tratada em frente específica (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`).
