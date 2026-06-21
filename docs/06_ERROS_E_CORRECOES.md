# PedroCore IA — Erros e Correções

Atualizado em: 21/06/2026

## V4.0.0 — Interface melhorada do chat

### Risco identificado

A V4 poderia quebrar o histórico local criado na V3 se a chave do `localStorage` fosse alterada.

### Correção aplicada

A chave `pedrocore:v3:chat-history` foi preservada por compatibilidade.

---

### Risco identificado

A interface poderia ficar grande demais dentro de `ChatPage.tsx`, dificultando manutenção nas próximas versões.

### Correção aplicada

Foi criada componentização leve com componentes específicos para sidebar, bolha de mensagem, campo de envio, loading e erro.

---

### Risco identificado

Um erro de backend desligado poderia continuar aparecendo como falha bruta ou mensagem confusa.

### Correção aplicada

Foi criado `ErrorBanner` com mensagem amigável e botão `Tentar novamente`.

---

### Risco identificado

O build TypeScript pode gerar arquivo `tsconfig.tsbuildinfo`, que não deve ser enviado como arquivo de versão.

### Correção aplicada

O `.gitignore` foi reforçado com `*.tsbuildinfo`.

---

### Risco identificado

A configuração local do Obsidian poderia aparecer no Git como `docs/.obsidian/`.

### Correção aplicada

O `.gitignore` foi reforçado com `docs/.obsidian/`.

---

### Risco identificado

A V4 poderia ser confundida com uma versão de arquitetura, banco, login ou provider.

### Correção aplicada

A documentação registra explicitamente que a V4 é apenas interface/UX, sem backend funcional novo.

## V3.0.0 — Histórico e feedback local

### Risco identificado

O histórico poderia ser perdido ao recarregar a página, pois antes as mensagens ficavam apenas no estado do React.

### Correção aplicada

Foi criada persistência local usando `localStorage`.

---

### Risco identificado

O `localStorage` poderia crescer indefinidamente.

### Correção aplicada

Foi definido limite técnico de 100 mensagens armazenadas localmente.

---

### Risco identificado

Feedback poderia ficar vinculado ao índice da lista e ser salvo na resposta errada.

### Correção aplicada

Cada mensagem recebeu identificador único.

## V2.0.0 — Multi-provider

### Risco identificado

Providers reais poderiam falhar por falta de chave local.

### Correção aplicada

Fallback para MockProvider preservado.
