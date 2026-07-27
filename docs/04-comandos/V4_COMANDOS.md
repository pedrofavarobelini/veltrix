# PedroCore IA V4.0.0 — Comandos PowerShell

Atualizado em: 21/06/2026

## Objetivo deste arquivo

Aplicar a V4.0.0 no projeto local, preservar o Git existente da pasta `C:\Projetos\pedrocore-ia`, testar backend/frontend, revisar documentação no Obsidian e salvar uma nova versão no Git local.

## Local oficial

```powershell
cd C:\Projetos\pedrocore-ia
```

## Regra crítica

Não apague a pasta `C:\Projetos\pedrocore-ia` inteira.

O ZIP da V4 deve ser copiado por cima do projeto existente para preservar:

- `.git` local;
- `.env` local;
- histórico de commits;
- tags anteriores;
- configuração local do projeto.

O ZIP da V4 não contém `.env`, `.git`, `node_modules`, `.venv`, `dist` ou caches.

---

# Terminal 1 — Antes de aplicar a V4: conferir Git local

```powershell
cd C:\Projetos\pedrocore-ia

git status

git log --oneline --decorate -5

git tag

git ls-files | Select-String "\.env"
```

## Resultado esperado

```txt
working tree clean
v3.0.0 no último commit
v2.0.0 preservada
apps/api/.env.example apenas
```

Se houver arquivos modificados antes da V4, revise antes de continuar.

---

# Terminal 1 — Aplicar ZIP normal da V4 preservando Git e `.env`

Coloque o arquivo baixado em `Downloads` com este nome:

```txt
pedrocore-ia-v4.0.0.zip
```

Depois rode:

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v4_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v4.0.0.zip" -DestinationPath "C:\Projetos\_pedrocore_v4_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v4_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v4_temp"
```

Esse processo copia os arquivos da V4 por cima do projeto atual sem apagar `.git` e sem apagar `.env`.

---

# Terminal 1 — Conferir alterações da V4 no Git

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git diff --stat
```

## Arquivos esperados na V4

```txt
.gitignore
README.md
VERSION.md
COMANDOS_POWERSHELL.md
apps/web/src/pages/ChatPage.tsx
apps/web/src/styles/global.css
apps/web/src/components/ChatSidebar.tsx
apps/web/src/components/MessageBubble.tsx
apps/web/src/components/ChatComposer.tsx
apps/web/src/components/LoadingBubble.tsx
apps/web/src/components/ErrorBanner.tsx
docs/04-comandos/V4_COMANDOS.md
docs/06_ERROS_E_CORRECOES.md
docs/08_CHANGELOG.md
docs/09_STATUS_ATUAL.md
docs/11_V4_INTERFACE_CHAT.md
```

---

# Terminal 2 — Rodar backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv sync

uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 3333
```

Não feche esse terminal.

---

# Terminal 3 — Rodar frontend

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

# Terminal 1 — Testar backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv run pytest
```

Resultado esperado:

```txt
7 passed
```

---

# Terminal 3 — Testar frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm run build
```

Se aparecer erro de dependência do Vite/Rolldown, rode:

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue

npm install

npm run build
```

---

# Teste manual obrigatório da V4

1. Abrir o frontend.
2. Conferir se a sidebar aparece.
3. Enviar mensagem com MockProvider.
4. Confirmar bolha do usuário à direita.
5. Confirmar resposta da IA à esquerda.
6. Confirmar timestamp na mensagem.
7. Clicar em `Copiar` na resposta.
8. Marcar `Gostei` e depois `Não gostei`.
9. Recarregar a página.
10. Confirmar que histórico e feedback continuam salvos.
11. Fechar o backend e enviar mensagem para validar erro visual.
12. Clicar em `Tentar novamente` depois de religar o backend.
13. Testar em janela menor para validar responsividade.
14. Clicar em `Limpar histórico` ou `Nova conversa`.

## Verificação no navegador

```txt
DevTools > Application > Local Storage > pedrocore:v3:chat-history
```

A chave continua com `v3` por compatibilidade com a V3.

---

# Terminal 1 — Atualizar Obsidian/documentação

A documentação já está dentro da pasta `docs`, em Markdown compatível com Obsidian.

Depois de aplicar o ZIP, abra no Obsidian a pasta:

```txt
C:\Projetos\pedrocore-ia\docs
```

Arquivos principais atualizados na V4:

```txt
docs/04-comandos/V4_COMANDOS.md
docs/06_ERROS_E_CORRECOES.md
docs/08_CHANGELOG.md
docs/09_STATUS_ATUAL.md
docs/11_V4_INTERFACE_CHAT.md
VERSION.md
README.md
COMANDOS_POWERSHELL.md
```

Para conferir pelo PowerShell:

```powershell
cd C:\Projetos\pedrocore-ia

Get-Content .\VERSION.md

Get-Content .\docs\09_STATUS_ATUAL.md

Get-Content .\docs\11_V4_INTERFACE_CHAT.md
```

---

# Terminal 1 — Salvar V4 no Git local

Só faça depois que os testes passarem e você aprovar a interface.

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git add -A

git reset docs/.obsidian/ 2>$null

git status --short

git commit -m "feat: melhorar interface do chat"
```

---

# Terminal 1 — Criar tag da V4

Só depois do commit:

```powershell
cd C:\Projetos\pedrocore-ia

git tag -a v4.0.0 -m "PedroCore IA V4 approved - improved chat interface"
```

---

# Terminal 1 — Conferência final

```powershell
cd C:\Projetos\pedrocore-ia

git log --oneline --decorate -5

git tag

git status

git ls-files | Select-String "\.env"
```

## Resultado esperado

```txt
NOVO_HASH (HEAD -> main, tag: v4.0.0) feat: melhorar interface do chat
0377e44 (tag: v3.0.0) feat: adicionar historico local e feedback das respostas
ea295c3 (tag: v2.0.0) feat: approve PedroCore IA V2 multi-provider
working tree clean
apps/api/.env.example
```

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
