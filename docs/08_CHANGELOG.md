# PedroCore IA — Changelog

Atualizado em: 04/07/2026

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
