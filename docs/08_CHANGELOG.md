# PedroCore IA — Changelog

Atualizado em: 21/06/2026

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
