# PedroCore IA — Status Atual

Atualizado em: 04/07/2026

## Status oficial

Em reformulação documental e estratégica. Este é o único documento de status oficial do projeto; prevalece sobre qualquer status antigo/duplicado ainda presente em `docs/`.

## Versão atual de produto

V5.1.9

## Frente atual

PEDROCORE-REPLAN-01E — Fechamento documental da reformulação.

`PEDROCORE-REPLAN-01A` (Consolidação documental e visão oficial), `PEDROCORE-REPLAN-01B` (Planejamento técnico e contratos), `PEDROCORE-REPLAN-01C` (Arquitetura-alvo) e `PEDROCORE-REPLAN-01D` (QA Intelligence) estão concluídas e commitadas:

- `1e5a8cb — docs: iniciar PEDROCORE-REPLAN-01A`
- `6e7badd — docs: planejar contratos PEDROCORE-REPLAN-01B`
- `c1e7816 — docs: definir arquitetura-alvo PEDROCORE-REPLAN-01C`
- `8c68b67 — docs: planejar QA Intelligence PEDROCORE-REPLAN-01D`

`PEDROCORE-REPLAN-01E` está sendo fechada documentalmente nesta etapa (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`). Após o commit aprovado da 01E, `PEDROCORE-REPLAN-01` ficará **concluída no escopo documental**. O próximo passo será planejar a primeira frente de implementação (`PEDROCORE-IMPLEMENT-01`, sugerida no documento de fechamento).

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

## Em andamento

- `PEDROCORE-REPLAN-01E` — fechamento documental da reformulação, consolidado em `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md` (escopo executado, commits, transição de visão, o que existe/não existe no código, decisões consolidadas, riscos remanescentes, pendências pós-reformulação e próxima fase recomendada). **Apenas documentação/planejamento — nenhum código foi criado.**

## Ainda não existe

- Task Router, Prompt Builder e Project Context implementados em código — apenas a arquitetura-alvo desses módulos foi documentada em `docs/11-arquitetura-alvo/` (`01C`).
- Endpoint novo de orquestração (`origin_system`/`task_type`/`artifacts`) — apenas especificado em `docs/10-contratos/`, não implementado.
- Resposta estruturada por tipo de tarefa (hoje a resposta é texto livre em `answer: str`).
- Provider Orchestration avançada (seleção por task_type/custo/qualidade) — apenas documentada como planejamento.
- Auditoria/log persistente de chamadas — apenas os campos planejados foram documentados; nenhum banco ou mecanismo de log foi criado.
- Artifact Reader real (leitura automática de pastas/arquivos externos, incluindo relatórios de QA do FinGuard) — planejado apenas como recebimento de conteúdo via payload; leitura automática de caminho/pasta é fase futura.
- QA Intelligence implementada em código — apenas a camada foi documentada em `docs/12-qa-intelligence/` (`01D`): não há parser de relatório, classificador de risco, endpoint de QA ou lógica de diagnóstico no código.
- Leitura real de arquivos do FinGuard — nenhuma leitura automática de repositório ou pasta do FinGuard existe; apenas o recebimento de conteúdo via payload é planejado.
- Análise visual real (`visual_qa_analysis`) — não há suporte multimodal implementado nem testado; é planejamento de fase futura.
- Persistência em banco de dados (histórico hoje só existe no navegador).
- Qualquer integração real com o FinGuard ou outro sistema externo.
- Qualquer módulo de `PEDROCORE-IMPLEMENT-01` (fase futura sugerida) — a implementação ainda não começou.

## Proibido nesta fase

- Alterar código-fonte (`apps/api`, `apps/web`).
- Alterar frontend, componentes, estilos, layout ou design.
- Instalar dependências ou rodar servidor/testes.
- Chamar providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok).
- Alterar `.env`.
- Ler ou escrever no repositório do FinGuard.
- Fazer commit ou remover documentação antiga nesta etapa.

## Riscos atuais

- **Documentação duplicada:** ainda existem pares de arquivos conflitantes em `docs/` (ex.: `docs/03_ROADMAP.md` vs `docs/03-versoes/ROADMAP.md`, `docs/09-status/STATUS_ATUAL.md` desatualizado) que não foram removidos nesta etapa, apenas sinalizados.
- **`GEMINI_API_KEY` configurada localmente:** o `.env` real do backend tem a chave do Gemini preenchida; qualquer execução do servidor com `provider=gemini` gera uma chamada real. Isso não foi alterado e deve ser tratado com cuidado em qualquer teste manual futuro.
- **Fallback Mock silencioso:** o fallback automático para `MockProvider` evita quebrar a interface, mas pode mascarar falhas reais de provider se o consumidor não checar explicitamente o campo `fallback_used` — especialmente relevante para futuros consumidores externos e para qualquer caso de uso de QA (ver Decisão Técnica 014).
- **Ausência de `task_type`/resposta estruturada:** a API atual não distingue tipos de tarefa nem devolve respostas estruturadas, o que limita o uso por sistemas externos além do chat conversacional atual.

## Próximos passos

- Concluir e revisar `PEDROCORE-REPLAN-01E` (fechamento documental em `docs/13-fechamento/`).
- Após aprovação/commit da 01E, considerar `PEDROCORE-REPLAN-01` concluída no escopo documental.
- Planejar `PEDROCORE-IMPLEMENT-01` — base inicial de orquestração por `task_type` (fase futura sugerida, ainda não iniciada).
- Saneamento de documentação duplicada/legada permanece como pendência futura, a ser tratada em frente específica (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`).
