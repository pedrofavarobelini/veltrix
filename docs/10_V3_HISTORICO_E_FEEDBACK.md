# V3 — Histórico Simples e Feedback Local

Atualizado em: 21/06/2026

## Objetivo

Adicionar histórico simples das conversas no frontend e permitir que o usuário registre feedback básico em cada resposta da IA.

## Escopo fechado

A V3 implementa:

- Salvamento local das mensagens.
- Exibição do histórico na interface.
- Persistência após recarregar a página.
- Feedback `Gostei` e `Não gostei` por resposta da IA.
- Botão para limpar histórico local.
- Limite técnico de 100 mensagens de conversa no histórico local.

## Fora do escopo

A V3 não implementa:

- Banco de dados.
- Login.
- Histórico por usuário.
- Sincronização entre dispositivos.
- RAG.
- Upload de documentos.
- Deploy.
- GitHub remoto.
- Integração com FinGuard.
- Treinamento do modelo com feedback.

## Decisão técnica

A persistência da V3 usa `localStorage` no frontend.

## Justificativa

Nesta fase, o objetivo é validar o fluxo de histórico e feedback sem aumentar a complexidade do backend. Banco de dados, usuários e sessões devem entrar apenas em versões futuras.

## Chave usada no navegador

```txt
pedrocore:v3:chat-history
```

## Estrutura da mensagem

```ts
type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  meta?: {
    provider: string;
    model: string;
    fallbackUsed: boolean;
    error?: string | null;
  };
  feedback?: "like" | "dislike" | null;
  isSystem?: boolean;
};
```

## Arquivos alterados

- `apps/web/src/pages/ChatPage.tsx`
- `apps/web/src/styles/global.css`
- `apps/web/src/types/chat.ts`
- `apps/web/src/utils/chatStorage.ts`
- `VERSION.md`
- `docs/09_STATUS_ATUAL.md`
- `docs/06_ERROS_E_CORRECOES.md`
- `docs/10_V3_HISTORICO_E_FEEDBACK.md`

## Testes obrigatórios

### Teste manual

1. Abrir backend.
2. Abrir frontend.
3. Enviar mensagem com MockProvider.
4. Verificar se a mensagem aparece no histórico.
5. Marcar `Gostei` em uma resposta.
6. Recarregar a página.
7. Confirmar que a conversa e o feedback continuam salvos.
8. Trocar para `Não gostei`.
9. Recarregar a página.
10. Confirmar que o novo feedback continua salvo.
11. Clicar em `Limpar histórico`.
12. Confirmar que o histórico foi removido.

### Teste técnico

No DevTools do navegador:

1. Abrir `Application`.
2. Abrir `Local Storage`.
3. Verificar a chave `pedrocore:v3:chat-history`.
4. Confirmar que mensagens e feedbacks estão salvos.

### Teste de build

Rodar no frontend:

```powershell
npm run build
```

### Teste do backend

Rodar na API:

```powershell
uv run pytest
```

## Critério de aprovação

A V3 só deve ser considerada aprovada depois que:

- O build do frontend passar.
- Os testes do backend passarem.
- O histórico persistir após recarregar a página.
- O feedback persistir após recarregar a página.
- O botão `Limpar histórico` funcionar.
- Nenhuma chave de API aparecer no Git.


## Git e versionamento

A V3 deve ser registrada no Git local somente depois da validação dos testes.

Comando de commit previsto:

```powershell
git commit -m "feat: adicionar historico local e feedback das respostas"
```

Tag prevista:

```powershell
git tag v3.0.0
```

A tag `v2.0.0` deve permanecer preservada.

## Documentação no Obsidian

A documentação da V3 está em Markdown dentro da pasta `docs`. Para revisar no Obsidian, abrir:

```txt
C:\Projetos\pedrocore-ia\docs
```

Arquivos diretamente relacionados à V3:

```txt
docs/04-comandos/V3_COMANDOS.md
docs/04-comandos/V3_GIT_VERSIONAMENTO.md
docs/06_ERROS_E_CORRECOES.md
docs/08_CHANGELOG.md
docs/09_STATUS_ATUAL.md
docs/10_V3_HISTORICO_E_FEEDBACK.md
```
