# V5.1.1 — Redesign real do front-end com logo oficial

## Objetivo

Corrigir o escopo visual da V5. A versão anterior tinha aplicado a logo e as configurações de provider, mas não aproximou suficientemente a interface do mockup aprovado. A V5.1 refaz a experiência visual do frontend React.

## Decisão técnica

A V5.1 mantém React + Vite + TypeScript e CSS próprio. Não foi adicionada biblioteca visual externa.

## O que mudou

- Criação de um header de marca com logo oficial.
- Reestruturação do layout em formato de console:
  - sidebar esquerda;
  - área central de chat;
  - painel direito de provider.
- Cards de provider visíveis no fluxo principal.
- Painel de configuração de provider integrado ao layout desktop.
- Bolhas de mensagens redesenhadas para tema escuro.
- Campo de envio redesenhado.
- Estado de erro visual mantido.
- Loading `Veltrix está pensando...` mantido com avatar da logo.
- Logo oficial aplicada no avatar da IA e favicon.

## O que foi preservado

- Backend FastAPI.
- Providers existentes.
- Chave Gemini no `.env` local do backend.
- Histórico local em `pedrocore:v3:chat-history`.
- Preferências de provider em `pedrocore:v5:provider-settings`.
- Documentação Obsidian.

## Fora do escopo

- Banco de dados.
- Login.
- RAG.
- Upload de documentos.
- Deploy.
- GitHub.
- Integração com FinGuard.

## Testes obrigatórios

- `uv run pytest` no backend.
- `npm run build` no frontend.
- Teste visual da sidebar, chat, provider strip e painel direito.
- Teste manual com MockProvider.
- Teste manual com GeminiProvider se `.env` estiver configurado.
- Conferência de que `.env` não foi versionado.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
