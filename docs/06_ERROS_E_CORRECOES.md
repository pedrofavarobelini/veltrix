# PedroCore IA — Erros e Correções

## Erro 001 — ZIP inicial com risco de pasta raiz errada

### Situação

O ZIP inicial poderia ser extraído criando uma estrutura de pasta incorreta.

### Correção aplicada

Foi definido o local oficial do projeto:

```txt
C:\Projetos\pedrocore-ia
```

### Status

Corrigido.

---

## Erro 002 — Caminho do projeto mal interpretado

### Situação

Havia risco de colocar o PedroCore IA dentro da pasta do FinGuard.

### Correção aplicada

Foi definido que o PedroCore IA é projeto irmão do FinGuard:

```txt
C:\Projetos\FinGuard
C:\Projetos\pedrocore-ia
```

### Status

Corrigido.

---

## Erro 003 — `uv` não reconhecido

### Situação

O PowerShell não reconhecia o comando `uv`.

### Diagnóstico

O `uv` ainda não estava instalado ou não estava disponível no PATH.

### Correção aplicada

O projeto passou a usar comandos organizados considerando instalação/sincronização com `uv`.

### Status

Corrigido.

---

## Erro 004 — `pip` não reconhecido

### Situação

O PowerShell não reconhecia o comando `pip`.

### Diagnóstico

O Python/pip não estava acessível diretamente no terminal.

### Correção aplicada

O fluxo passou a priorizar `uv`, evitando depender de `pip` diretamente.

### Status

Contornado com `uv`.

---

## Erro 005 — Documentação incompleta

### Situação

O projeto precisava registrar decisões, comandos, erros, testes e status em Markdown.

### Correção aplicada

Foi criada e mantida documentação compatível com Obsidian dentro da pasta `docs`.

### Status

Corrigido.

---

## Erro 006 — `GET /` retornava 404

### Situação

A rota raiz da API retornava erro 404.

### Correção aplicada

Na V1.0.1, foi adicionada a rota raiz `/`.

### Status

Corrigido.

---

## Erro 007 — Botões sem feedback visual

### Situação

Os botões do frontend não exibiam retorno visual claro após clique.

### Correção aplicada

Na V1.0.1, foi adicionado toast visual no frontend.

### Status

Corrigido.

---

## Erro 008 — Script de patch colado parcialmente no PowerShell

### Situação

Um bloco que deveria criar um `.ps1` foi executado parcialmente no PowerShell.

### Diagnóstico

Variáveis ficaram nulas e o PowerShell tentou escrever em caminhos incorretos, como `C:\05_TESTES.md`.

### Correção aplicada

Foi gerado um novo ZIP revisado para substituir o fluxo quebrado.

### Status

Corrigido.

---

## Correção 009 — Toast com tempo inconsistente e configurações simples demais

Atualizado em: 20/06/2026 17:32:24

### Situação

Após a V1.0.1, as mensagens de feedback começaram a aparecer, mas o tempo do toast ficava inconsistente ao clicar rapidamente em botões diferentes.

Também foi identificado que o painel de configurações estava simples demais e exibia mensagens desnecessárias ao abrir/fechar.

### Diagnóstico

O toast usava `setTimeout` sem limpar o timer anterior. Assim, um timer antigo podia apagar uma mensagem nova antes do tempo esperado.

### Correção aplicada

- Adicionado `useRef` para controlar o timer do toast.
- O timer anterior passou a ser cancelado antes de abrir uma nova mensagem.
- Removidas mensagens ao abrir/fechar configurações.
- Painel de configurações recebeu melhorias visuais.
- Botão simples de fechar foi substituído por botão X, Cancelar e Salvar e fechar.

### Arquivos alterados

- `apps/web/src/pages/ChatPage.tsx`
- `apps/web/src/styles/global.css`

### Status

Corrigido.

---

## Correção 010 — Ajuste incremental da interface

Atualizado em: 20/06/2026

### Situação

A interface precisava manter o padrão visual após os ajustes de toast e configurações.

### Correção aplicada

Foram mantidos os ajustes visuais no frontend e registrada a evolução incremental antes da V1.0.4.

### Status

Corrigido.

---

## Correção 011 — Acentuação quebrada na interface

Atualizado em: 20/06/2026 17:49:35

### Situação

A interface passou a exibir caracteres incorretos no lugar de acentos.

Exemplos:

- Configurações
- Técnico
- Você
- Não gostei

### Diagnóstico

O arquivo React foi salvo anteriormente com problema de encoding durante aplicação de patch via PowerShell.

### Correção aplicada

O arquivo `ChatPage.tsx` foi regravado em UTF-8 para preservar acentuação.

### Arquivo alterado

- `apps/web/src/pages/ChatPage.tsx`

### Status

Corrigido.

---

## Correção 012 — Texto Unicode aparecendo na interface

Atualizado em: 20/06/2026 18:04:59

### Situação

A interface exibiu textos quebrados como:

```txt
Configura\u00e7\u00f5es
T\u00e9cnico
N\u00e3o gostei
```

### Diagnóstico

A tentativa anterior usou escapes Unicode de forma incorreta, fazendo com que eles aparecessem visualmente na tela.

### Correção aplicada

O arquivo `ChatPage.tsx` foi regravado em UTF-8 com textos diretos e centralizados no objeto `UI`.

### Arquivo alterado

```txt
apps\web\src\pages\ChatPage.tsx
```

### Status

Corrigido.

---

## Correção 013 — Feedback global não persistente

Atualizado em: 21/06/2026

### Situação

Antes da V3, o botão `Gostei`/`Não gostei` usava um estado global da tela. Isso fazia o feedback valer visualmente para a interface, mas não ficava vinculado de forma segura a uma resposta específica nem sobrevivia ao recarregamento da página.

### Diagnóstico

O feedback estava separado do objeto da mensagem. Sem identificador único por resposta, o sistema poderia confundir feedbacks quando o histórico crescesse.

### Correção aplicada

- Criado tipo `ChatMessage` com `id`, `role`, `content`, `createdAt`, `meta` e `feedback`.
- Cada mensagem passou a ter identificador único.
- O feedback passou a ser salvo diretamente na resposta da IA.
- O feedback passou a ser persistido via `localStorage`.

### Arquivos alterados

- `apps/web/src/pages/ChatPage.tsx`
- `apps/web/src/types/chat.ts`
- `apps/web/src/utils/chatStorage.ts`

### Status

Corrigido na V3.0.0.

---

## Correção 014 — Histórico perdido ao recarregar a página

Atualizado em: 21/06/2026

### Situação

Antes da V3, as mensagens ficavam apenas no estado do React. Ao recarregar a página, o histórico era perdido.

### Diagnóstico

Não existia camada de persistência local para conversas.

### Correção aplicada

- Criado armazenamento local com a chave `pedrocore:v3:chat-history`.
- Criada leitura segura do histórico salvo.
- Criado salvamento automático do histórico quando as mensagens mudam.
- Criado botão para limpar histórico local.

### Arquivos alterados

- `apps/web/src/pages/ChatPage.tsx`
- `apps/web/src/utils/chatStorage.ts`
- `apps/web/src/styles/global.css`

### Status

Corrigido na V3.0.0.

---

## Correção 015 — Risco de crescimento indefinido do histórico local

Atualizado em: 21/06/2026

### Situação

Um histórico salvo sem limite poderia crescer indefinidamente no navegador.

### Diagnóstico

O `localStorage` tem limite de armazenamento e pode falhar se muitos dados forem salvos.

### Correção aplicada

Foi definido limite técnico de 100 mensagens de conversa no histórico local.

### Arquivos alterados

- `apps/web/src/utils/chatStorage.ts`

### Status

Corrigido preventivamente na V3.0.0.

---

## Correção 016 — ZIP de origem enviado com `.env` local

Atualizado em: 21/06/2026

### Situação

O ZIP usado como fonte para a V3 continha o arquivo local `apps/api/.env`.

### Diagnóstico

O arquivo não estava versionado no Git, pois o `.gitignore` protege `.env` e `.env.*`, mantendo exceção apenas para `.env.example`. Porém, ao compactar a pasta completa manualmente, o `.env` foi incluído no ZIP.

### Correção preventiva aplicada

- O conteúdo do `.env` não foi exibido nem documentado.
- A entrega da V3 foi gerada sem `.env`, `.venv`, `node_modules`, `.git`, caches e arquivos temporários.
- A orientação permanece: nunca enviar `.env` para GitHub e nunca compartilhar ZIP completo contendo chaves reais.

### Status

Corrigido preventivamente na entrega da V3.0.0.

---

## Correção 017 — Documentação e comandos revisados para ZIP único da V3

Atualizado em: 21/06/2026

### Situação

A primeira entrega da V3 separava patch e fonte limpa, o que poderia confundir o fluxo de instalação.

### Correção aplicada

- A entrega foi normalizada em um ZIP principal da V3.
- O arquivo `COMANDOS_POWERSHELL.md` foi atualizado para V3.0.0.
- Foram removidos arquivos locais desnecessários da entrega, como backups `.bak`, `.git`, `.env`, `.venv`, `node_modules`, `dist` e caches.
- A documentação com acentuação quebrada foi revisada.

### Status

Corrigido na entrega revisada da V3.0.0.
