# PedroCore IA V3.0.0 — Comandos PowerShell

## Local oficial

```powershell
cd C:\Projetos\pedrocore-ia
```

## Antes de rodar

A V3 não vem com `.env` no ZIP por segurança. Se você já tem o projeto instalado em `C:\Projetos\pedrocore-ia`, mantenha o arquivo:

```txt
C:\Projetos\pedrocore-ia\apps\api\.env
```

Esse arquivo contém a chave real do Gemini e não deve ir para GitHub.

---

## Terminal 1 — Conferir segurança e estado do projeto

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git ls-files | Select-String "\.env"
```

### Resultado esperado

Pode aparecer:

```txt
apps/api/.env.example
```

Não pode aparecer:

```txt
apps/api/.env
```

Se `apps/api/.env` aparecer como versionado, pare antes de continuar.

---

## Terminal 2 — Rodar backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv sync

uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 3333
```

Não feche esse terminal.

---

## Terminal 3 — Rodar frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm install

npm run dev
```

Abra no navegador:

```txt
http://localhost:5173
```

---

## Terminal 1 — Testar backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv run pytest
```

Resultado esperado:

```txt
7 passed
```

---

## Terminal 3 — Testar frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm run build
```

Se aparecer erro de dependência do Vite, rode:

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm install

npm run build
```

---

## Terminal 4 — Teste direto da API

### Health

```powershell
Invoke-RestMethod -Uri "http://localhost:3333/health" -Method GET
```

### Providers

```powershell
Invoke-RestMethod -Uri "http://localhost:3333/api/providers" -Method GET
```

### Chat com Mock

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:3333/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"message":"Teste com Mock","mode":"tecnico","provider":"mock","model":"mock-v1","system_prompt":"Você é o PedroCore IA."}'
```

### Chat com Gemini

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:3333/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"message":"Explique FastAPI em poucas linhas.","mode":"tecnico","provider":"gemini","model":"gemini-3.5-flash","system_prompt":"Você é o PedroCore IA."}'
```

O Gemini só responde como provider real se `GEMINI_API_KEY` estiver configurada no `.env` local.

---

## Teste manual obrigatório da V3

1. Abrir o frontend.
2. Enviar uma mensagem com MockProvider.
3. Confirmar que a mensagem aparece no histórico.
4. Marcar `Gostei` em uma resposta.
5. Recarregar a página.
6. Confirmar que a conversa e o feedback continuam salvos.
7. Trocar para `Não gostei`.
8. Recarregar a página.
9. Confirmar que o feedback atualizado continua salvo.
10. Clicar em `Limpar histórico`.
11. Confirmar que o histórico foi apagado.

---

## Verificação do localStorage

No navegador:

1. Abra o DevTools.
2. Entre em `Application`.
3. Entre em `Local Storage`.
4. Confira a chave:

```txt
pedrocore:v3:chat-history
```

---

## Commit local depois da aprovação

Execute somente depois que a V3 for testada e aprovada visualmente.

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git add README.md VERSION.md COMANDOS_POWERSHELL.md .gitignore apps/web/src/pages/ChatPage.tsx apps/web/src/styles/global.css apps/web/src/types/chat.ts apps/web/src/utils/chatStorage.ts docs/04-comandos/V3_COMANDOS.md docs/06_ERROS_E_CORRECOES.md docs/08_CHANGELOG.md docs/09_STATUS_ATUAL.md docs/10_V3_HISTORICO_E_FEEDBACK.md

git commit -m "feat: adicionar historico local e feedback das respostas"
```
