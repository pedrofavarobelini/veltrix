# V3 — Comandos PowerShell

Atualizado em: 21/06/2026

## Objetivo

Comandos para testar a V3 do PedroCore IA no Windows usando PowerShell.

## Terminal 1 — Conferir projeto e segurança

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git ls-files | Select-String "\.env"
```

### Resultado esperado

- `.env` não deve aparecer como arquivo versionado.
- `.env.example` pode aparecer.

Se `apps/api/.env` aparecer em `git ls-files`, pare. O arquivo sensível foi versionado e precisa ser removido do Git antes de continuar.

## Terminal 2 — Rodar backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 3333
```

## Terminal 3 — Rodar frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm run dev
```

Abrir no navegador:

```txt
http://localhost:5173
```

## Terminal 1 — Testar backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv run pytest
```

## Terminal 3 — Testar frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm run build
```

## Teste manual da V3

1. Abrir frontend.
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

## Verificação do localStorage

No navegador:

1. Abrir DevTools.
2. Abrir `Application`.
3. Abrir `Local Storage`.
4. Conferir a chave:

```txt
pedrocore:v3:chat-history
```

## Commit local depois da aprovação

Só execute depois que a V3 for aprovada visualmente.

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git add README.md VERSION.md apps/web/src/pages/ChatPage.tsx apps/web/src/styles/global.css apps/web/src/types/chat.ts apps/web/src/utils/chatStorage.ts docs/06_ERROS_E_CORRECOES.md docs/08_CHANGELOG.md docs/09_STATUS_ATUAL.md docs/10_V3_HISTORICO_E_FEEDBACK.md docs/04-comandos/V3_COMANDOS.md

git commit -m "feat: adicionar historico local e feedback das respostas"
```
