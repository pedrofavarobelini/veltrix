# PedroCore IA — Changelog

Atualizado em: 21/06/2026

## V4.0.0 — Interface melhorada do chat

Status: implementada para testes.

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

### Alterado

- `ChatPage.tsx` reorganizado para usar componentes menores.
- `global.css` refeito para a interface V4.
- `README.md`, `VERSION.md`, `COMANDOS_POWERSHELL.md` e documentação de status atualizados.
- `.gitignore` reforçado para ignorar `*.tsbuildinfo` e configuração local do Obsidian.

### Mantido

- Backend FastAPI preservado.
- Providers preservados.
- Estrutura multi-provider preservada.
- Histórico local da V3 preservado.
- Chave `pedrocore:v3:chat-history` preservada por compatibilidade.

### Não implementado

- Banco de dados.
- Login.
- RAG.
- Deploy.
- GitHub.
- Integração com FinGuard.

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
