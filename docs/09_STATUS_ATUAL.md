# PedroCore IA — Status Atual

Atualizado em: 04/07/2026

## Status oficial

Reformulação documental (`PEDROCORE-REPLAN-01`) concluída; implementação inicial de código em andamento (`PEDROCORE-IMPLEMENT-01`). Este é o único documento de status oficial do projeto; prevalece sobre qualquer status antigo/duplicado ainda presente em `docs/`.

## Versão atual de produto

V5.1.9

## Frente atual

PEDROCORE-IMPLEMENT-01A/01B — Task Router mínimo + metadados de resposta.

`PEDROCORE-REPLAN-01` (01A a 01E) está **concluída no escopo documental** e commitada:

- `1e5a8cb — docs: iniciar PEDROCORE-REPLAN-01A`
- `6e7badd — docs: planejar contratos PEDROCORE-REPLAN-01B`
- `c1e7816 — docs: definir arquitetura-alvo PEDROCORE-REPLAN-01C`
- `8c68b67 — docs: planejar QA Intelligence PEDROCORE-REPLAN-01D`
- `cc808a7 — docs: fechar PEDROCORE-REPLAN-01E`

A implementação inicial de código começou após o fechamento documental, com a primeira frente `PEDROCORE-IMPLEMENT-01` (base inicial de orquestração por `task_type`).

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
- `PEDROCORE-IMPLEMENT-01A/01B` — Task Router mínimo implementado em código: `task_type`, `origin_system`, `context` e `metadata` opcionais no `ChatRequest`; Task Router mínimo em `apps/api/app/modules/task_router/` reconhecendo 7 task_types + `unknown`, sem bloqueio duro; metadados de tarefa (`task_type`, `origin_system`, `task_criticality`, `requires_structured_response`, `task_warnings`) no `ChatResponse`; warning forte quando fallback Mock ocorre em tarefa crítica; testes backend em `apps/api/tests/test_task_router.py` (8 testes, `15 passed, 2 warnings` no total). Commitada em `577bc88`. Working tree limpo após o commit.

## Em andamento

Nenhuma frente em andamento no momento — `PEDROCORE-IMPLEMENT-01A/01B` está implementada, validada e commitada. Próxima etapa (`PEDROCORE-IMPLEMENT-01C/01D`) ainda não iniciada.

## Ainda não existe

- Prompt Builder real — o prompt continua montado por `BaseAIProvider.build_prompt`, sem usar `task_type`, `context` ou `metadata` na montagem.
- Project Context real — nenhuma representação/configuração de sistema externo (ex.: FinGuard) existe em código; apenas o conceito foi documentado em `docs/11-arquitetura-alvo/PROJECT_CONTEXT.md`.
- Artifact Reader — nenhuma leitura de artefato (via payload ou automática) foi implementada.
- QA Intelligence real — o Task Router reconhece os `task_type` de QA e sinaliza criticidade/warnings, mas não há parser de relatório, classificador de risco ou lógica de diagnóstico.
- Audit/logs — nenhum banco ou mecanismo de log foi criado.
- Endpoint `/api/orchestrate` ou qualquer endpoint novo de orquestração — o Task Router opera internamente dentro de `POST /api/chat` (Decisão Técnica 039).
- Resposta estruturada real por tipo de tarefa (o `ChatResponse` sinaliza `requires_structured_response`, mas a resposta em si continua sendo `answer: str` livre).
- Provider Orchestration avançada (seleção por task_type/custo/qualidade) — apenas documentada como planejamento; a seleção de provider continua manual/por default.
- Leitura real de arquivos do FinGuard — nenhuma leitura automática de repositório ou pasta do FinGuard existe.
- Análise visual real (`visual_qa_analysis`) — não há suporte multimodal implementado nem testado.
- Persistência em banco de dados (histórico hoje só existe no navegador).
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

- `PEDROCORE-IMPLEMENT-01C/01D` — Prompt Builder mínimo + Project Context mínimo (ainda não iniciado). Prompt Builder e Project Context reais ainda não existem no código; Artifact Reader e QA Intelligence real também não existem; nenhuma integração real com o FinGuard existe.
- Planejar Audit/logs básico antes de qualquer integração real com sistemas externos.
- Saneamento de documentação duplicada/legada permanece como pendência futura, a ser tratada em frente específica (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`).
