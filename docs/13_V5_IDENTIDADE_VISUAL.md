# V5 — Identidade visual oficial

## Objetivo

Aplicar a logo oficial escolhida para o PedroCore IA sem alterar o design aprovado da V5.

## Escopo aplicado

- Logo oficial adicionada em `apps/web/src/assets/pedrocore-logo-icon.png`.
- Favicon atualizado em `apps/web/public/favicon-32.png`.
- Ícone de aplicativo atualizado em `apps/web/public/logo192.png`.
- Sidebar passou a usar a logo oficial no bloco da marca.
- Avatar das respostas da IA passou a usar a logo oficial.
- Layout, cores, estrutura de providers, histórico, chat e painel da V5 foram preservados.

## Arquivos principais

```txt
apps/web/src/assets/pedrocore-logo-icon.png
apps/web/public/favicon-32.png
apps/web/public/logo192.png
apps/web/src/components/ChatSidebar.tsx
apps/web/src/components/MessageBubble.tsx
apps/web/src/styles/global.css
apps/web/index.html
```

## Decisão técnica

A logo foi aplicada como imagem estática importada no React, mantendo o texto `PedroCore IA` renderizado pela interface. Isso evita usar uma arte grande com texto rasterizado dentro da UI e mantém melhor responsividade.

## Limitação

A logo foi extraída a partir da imagem enviada pelo usuário. Para uma versão ainda mais profissional, recomenda-se futuramente substituir por SVG ou PNG transparente original da logo oficial.

## Fora do escopo

- Não houve mudança no backend.
- Não houve mudança em providers.
- Não houve banco de dados.
- Não houve login.
- Não houve GitHub.
- Não houve deploy.
- Não houve RAG.
- Não houve integração com FinGuard.

## Testes obrigatórios

- Rodar `uv run pytest` no backend.
- Rodar `npm run build` no frontend.
- Conferir a logo na sidebar.
- Conferir a logo no avatar da IA.
- Conferir favicon no navegador.
- Enviar mensagem com MockProvider.
- Enviar mensagem com GeminiProvider se a chave estiver configurada no `.env`.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
