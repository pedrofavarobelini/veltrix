# Fechamento — PEDROCORE-REPLAN-01

> Documento de fechamento documental da frente `PEDROCORE-REPLAN-01`. Este documento consolida o que foi entregue nas etapas 01A a 01E. **Nada aqui foi implementado em código** — o fechamento é exclusivamente documental e arquitetural, preparando o terreno para uma futura fase de implementação.

## 1. Objetivo da frente

`PEDROCORE-REPLAN-01` foi criada para reposicionar o Veltrix de "chat pessoal multi-provider" para **orquestrador central de IA do ecossistema Pedro**, documentando desde a visão estratégica até os contratos técnicos, a arquitetura-alvo e o caso de uso de QA Intelligence — sempre como planejamento, sem alterar o código existente, o frontend ou o design.

## 2. Escopo executado

- **01A — Consolidação documental e visão oficial.** Reformulação de README, VERSION, visão geral, objetivo, roadmap, status, decisões técnicas e changelog.
- **01B — Planejamento técnico e contratos.** Especificação do contrato de orquestração (`origin_system`, `task_type`, `context`, `artifacts`), tipos de tarefa, resposta padronizada e contrato de QA Intelligence.
- **01C — Arquitetura-alvo.** Documentação de Task Router, Prompt Builder, Project Context, Provider Orchestration, Structured Responses, Artifact Reader e Audit/logs.
- **01D — QA Intelligence.** Documentação da camada futura de análise de relatórios, diagnóstico de falhas e release gate assistido.
- **01E — Fechamento documental.** Este documento e a consolidação final da frente.

## 3. Commits da frente

- `1e5a8cb` — docs: iniciar PEDROCORE-REPLAN-01A
- `6e7badd` — docs: planejar contratos PEDROCORE-REPLAN-01B
- `c1e7816` — docs: definir arquitetura-alvo PEDROCORE-REPLAN-01C
- `8c68b67` — docs: planejar QA Intelligence PEDROCORE-REPLAN-01D
- commit da 01E ainda pendente até aprovação e commit final

## 4. O que mudou na visão do projeto

**Antes:** o Veltrix era tratado principalmente como chat/API multi-provider para testes e uso pessoal — a documentação original (V1 a V5.1.9) descrevia um assistente de testes de resposta de IA, sem noção de orquestração central, contratos externos ou análise operacional.

**Agora:** o Veltrix é documentado como **provedor/orquestrador central de IA** para sistemas externos do ecossistema Pedro, com contratos de entrada/saída planejados, arquitetura-alvo desenhada (Task Router, Prompt Builder, Project Context, Provider Orchestration, Structured Responses, Artifact Reader, Audit/logs) e um caso de uso concreto de QA Intelligence planejado para apoiar o QA Automation do FinGuard.

## 5. O que existe hoje no código

- Backend FastAPI (`apps/api`).
- `GET /`.
- `GET /health`.
- `POST /api/chat`.
- `GET /api/providers`.
- `ChatService` (orquestração simples atual: resolve provider, aplica fallback).
- `ProviderRegistry`.
- Providers: `MockProvider`, `GeminiProvider`, `OpenAIProvider`, `ClaudeProvider`, `DeepSeekProvider`, `GrokProvider` (todos via `BaseAIProvider`).
- Fallback automático para `MockProvider` quando um provider real falha ou não está configurado.
- Frontend React/Vite/TypeScript preservado (V5.1.9), consumindo `/api/chat` e `/api/providers`.
- Histórico de mensagens e feedback (gostei/não gostei) salvos localmente no navegador (`localStorage`).
- Testes de backend existentes (`apps/api/tests`), cobrindo chat mock, fallback por provider desconhecido, validação de payload e listagem de providers.

## 6. O que ainda não existe no código

- Task Router.
- Prompt Builder.
- Project Context.
- Artifact Reader.
- QA Intelligence.
- Audit/logs.
- Resposta estruturada por `task_type`.
- Endpoint `/api/orchestrate` (ou qualquer endpoint novo de orquestração).
- Integração real com o FinGuard.
- Leitura automática de arquivos externos (de qualquer sistema, incluindo o FinGuard).
- Análise visual real (`visual_qa_analysis`).
- Persistência backend (histórico hoje só existe no `localStorage` do navegador).
- Autenticação própria para sistemas externos.

## 7. Documentos oficiais criados ou consolidados

- `README.md`
- `VERSION.md`
- `docs/00-visao-geral/README.md`
- `docs/00-visao-geral/OBJETIVO.md`
- `docs/03-versoes/ROADMAP.md`
- `docs/09_STATUS_ATUAL.md`
- `docs/07-decisoes/DECISOES_TECNICAS.md`
- `docs/08_CHANGELOG.md`
- `docs/10-contratos/` (contratos técnicos: `CONTRATOS_TECNICOS_PEDROCORE.md`, `CONTRATO_ORQUESTRACAO.md`, `CONTRATO_QA_INTELLIGENCE.md`)
- `docs/11-arquitetura-alvo/` (arquitetura-alvo: `ARQUITETURA_ALVO_PEDROCORE.md`, `TASK_ROUTER.md`, `PROMPT_BUILDER.md`, `PROJECT_CONTEXT.md`)
- `docs/12-qa-intelligence/` (QA Intelligence: `QA_INTELLIGENCE_OVERVIEW.md`, `QA_REPORT_ANALYSIS.md`, `QA_FAILURE_DIAGNOSIS.md`, `QA_RELEASE_GATE.md`)
- `docs/13-fechamento/` (este documento)

## 8. Relação com o FinGuard

- O FinGuard é um projeto externo e independente.
- **O FinGuard não foi alterado** em nenhuma etapa de `PEDROCORE-REPLAN-01` — nenhum arquivo, migration, seed, teste ou configuração do FinGuard foi tocado.
- O QA Automation pertence ao FinGuard e continua responsável pela validação técnica (API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências).
- `QA-AUTOMATION-01G` (agente exploratório assistido por IA) foi delegado ao Veltrix como **caso de uso futuro**, documentado em `docs/12-qa-intelligence/`.
- O Veltrix poderá, no futuro, receber artefatos do FinGuard por payload/entrada controlada — nunca por acesso direto ao repositório ou à infraestrutura do FinGuard.
- O Veltrix **não lê arquivos reais do FinGuard automaticamente**.
- O Veltrix **não roda testes do FinGuard**.
- O Veltrix **não altera o FinGuard** de nenhuma forma.
- O Veltrix **não calcula números financeiros oficiais** do FinGuard.

## 9. Decisões arquiteturais consolidadas

- Veltrix como orquestrador central de IA do ecossistema Pedro (Decisão 007).
- **Task Router decide. Prompt Builder monta. Provider executa.** (Decisões 022, 023).
- Sistemas externos devem enviar `origin_system` e `task_type` em contratos futuros (Decisão 017).
- Respostas críticas devem ser estruturadas (Decisão 018).
- Artifact Reader futuro deve ser somente leitura e não pode executar comandos em projetos externos (Decisão 026).
- Mock não pode validar tarefas críticas silenciosamente (Decisões 014, 020, 030).
- QA Intelligence analisa; não executa testes nem substitui o QA Automation (Decisões 021, 028).
- `can_advance` é recomendação assistida, nunca autorização automática (Decisão 031).
- Frontend e design ficam congelados durante toda a reformulação (Decisão 015).

## 10. Riscos remanescentes

- **Documentação duplicada/legada ainda existe** — pares de arquivos conflitantes em `docs/` (ex.: `docs/03_ROADMAP.md` vs `docs/03-versoes/ROADMAP.md`, `docs/09-status/STATUS_ATUAL.md` desatualizado) não foram removidos em nenhuma etapa desta frente.
- **`.env` local tem `GEMINI_API_KEY` configurada** — qualquer execução do servidor com `provider=gemini` gera uma chamada real; isso não foi alterado por esta reformulação.
- **O fallback Mock atual é amplo** e pode mascarar falhas se usado sem cuidado, especialmente por futuros consumidores externos que não checarem `fallback_used`.
- **Versão de produto V5.1.9 e versão backend 0.2.0 ainda convivem**, sem terem sido unificadas ou renomeadas.
- **Não há autenticação entre sistemas externos e o Veltrix** — qualquer integração real precisaria disso antes de ir a produção.
- **Não há audit/log** implementado — apenas os campos foram planejados.
- **Não há persistência backend** — o histórico continua vivendo somente no navegador.
- **Não há proteção explícita contra chamada acidental a provider real** além da configuração atual (ausência de chave); a Decisão 013 já registra essa lacuna como algo a resolver em implementação futura.

## 11. Pendências pós-reformulação

- Saneamento de documentação legada/duplicada (pastas antigas numeradas na raiz de `docs/`, pastas vazias, arquivos `.bak-*` versionados).
- Definir a primeira frente de implementação.
- Desenhar a implementação incremental do Task Router.
- Desenhar a resposta estruturada inicial (schema Pydantic, validação).
- Decidir a estratégia de "safe mode" para providers reais (controle explícito além da ausência de chave).
- Decidir autenticação/API key para sistemas externos consumirem o Veltrix.
- Planejar audit/log em detalhe técnico (armazenamento, retenção, formato).
- Planejar persistência (banco de dados, migrations, se aplicável).
- Planejar o Artifact Reader somente leitura em detalhe técnico (formato de recebimento de artefatos visuais, limites de tamanho).
- Planejar QA Intelligence textual (relatórios, logs, diagnóstico) antes de qualquer capacidade visual/exploratória.

## 12. Próxima fase recomendada

A próxima fase recomendada é **implementação incremental**, começando pequeno e mantendo tudo compatível com o que já existe.

**Sugestão de próxima frente:** `PEDROCORE-IMPLEMENT-01` — Base inicial de orquestração por `task_type`.

Escopo futuro sugerido (a ser detalhado e aprovado antes de iniciar):

- Não mexer no frontend.
- Manter `/api/chat` compatível.
- Criar schemas internos ou planejados para o novo contrato.
- Implementar um `task_type` mínimo (ex.: apenas `general_chat` e um segundo tipo simples).
- Preservar o `MockProvider` como ambiente seguro padrão de desenvolvimento/teste.
- Não tocar no FinGuard.
- Não chamar provider real sem controle explícito.

Esta é apenas uma recomendação de escopo; a decisão de abrir `PEDROCORE-IMPLEMENT-01` e seu escopo definitivo dependem de aprovação em uma etapa futura, fora desta frente documental.

---

## Navegacao

- [[MOC_FECHAMENTOS]]
- [[MOC_VELTRIX]]
