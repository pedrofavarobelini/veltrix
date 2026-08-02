# V4 — Interface melhorada do chat

Atualizado em: 21/06/2026

## Objetivo

Melhorar a interface do PedroCore IA no frontend React, deixando o chat mais limpo, profissional, responsivo e preparado para as próximas versões.

## Escopo fechado da V4

A V4 é uma versão de experiência de uso e interface.

Entrou na V4:

- Sidebar de histórico local.
- Layout principal reorganizado.
- Bolhas modernas de mensagem.
- Separação visual clara entre usuário e IA.
- Botão copiar resposta.
- Feedback `Gostei` e `Não gostei` com estado visual.
- Timestamp simples por mensagem.
- Estado de carregamento `PedroCore está pensando...`.
- Erro visual com botão `Tentar novamente`.
- Métricas simples da conversa.
- Responsividade para telas menores.
- Componentização leve da interface React.

Não entrou na V4:

- Banco de dados.
- Login.
- GitHub.
- Deploy.
- RAG.
- Upload de arquivos.
- Provider novo real.
- Integração com FinGuard.
- Sistema real de múltiplas conversas.

## Decisão técnica

A V4 iniciou uma componentização leve do frontend React.

Componentes criados:

```txt
apps/web/src/components/ChatSidebar.tsx
apps/web/src/components/MessageBubble.tsx
apps/web/src/components/ChatComposer.tsx
apps/web/src/components/LoadingBubble.tsx
apps/web/src/components/ErrorBanner.tsx
```

Arquivos principais alterados:

```txt
apps/web/src/pages/ChatPage.tsx
apps/web/src/styles/global.css
```

## Por que não foi usada biblioteca visual externa

A V4 usa CSS próprio para evitar dependências desnecessárias. Nesta fase, instalar Material UI, Tailwind, shadcn/ui ou outro kit visual aumentaria complexidade sem necessidade.

A prioridade da V4 é melhorar a interface mantendo estabilidade.

## Persistência

A V4 preserva a persistência da V3 via `localStorage`.

Chave mantida:

```txt
pedrocore:v3:chat-history
```

A chave não foi renomeada para evitar perda do histórico local já salvo no navegador.

## Limitações

- O histórico ainda é local e limitado ao navegador atual.
- O botão `Nova conversa` limpa o histórico local atual; ainda não cria uma sessão separada real.
- O feedback ainda não altera respostas futuras.
- O erro visual depende do frontend detectar falha na chamada da API.
- Tema claro/escuro automático depende da preferência do sistema operacional.

## Testes obrigatórios

- Rodar backend com `uv run pytest`.
- Rodar frontend com `npm run build`.
- Enviar mensagem com MockProvider.
- Validar resposta com GeminiProvider quando a chave local existir.
- Testar copiar resposta.
- Testar gostei/não gostei.
- Recarregar navegador e confirmar persistência.
- Testar erro visual com backend desligado.
- Testar layout em tela menor.

## Resultado esperado

A V4 deve deixar o PedroCore IA com aparência de protótipo profissional, mas sem alterar a arquitetura principal do projeto.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
