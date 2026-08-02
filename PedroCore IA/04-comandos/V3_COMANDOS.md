# V3 — Comandos PowerShell

Atualizado em: 21/06/2026

## Objetivo

Aplicar, testar e validar a V3.0.0 do PedroCore IA no Windows usando PowerShell, preservando o Git local da pasta `C:\Projetos\pedrocore-ia`.

## Importante

Não apagar a pasta inteira do projeto. A V3 deve ser copiada por cima do projeto atual para preservar `.git` e `.env` locais.

---

## Terminal 1 — Conferir Git antes da V3

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git branch

git tag

git log --oneline --decorate -5
```

A tag `v2.0.0` deve existir.

---

## Terminal 1 — Conferir segurança do `.env`

```powershell
cd C:\Projetos\pedrocore-ia

git ls-files | Select-String "\.env"
```

Resultado correto:

```txt
apps/api/.env.example
```

Não pode aparecer:

```txt
apps/api/.env
```

---

## Terminal 1 — Aplicar ZIP da V3

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v3_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v3.0.0.zip" -DestinationPath "C:\Projetos\_pedrocore_v3_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v3_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v3_temp"
```

---

## Terminal 1 — Conferir alterações após aplicar

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git diff --stat
```

---

## Terminal 2 — Rodar backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv sync

uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 3333
```

---

## Terminal 3 — Rodar frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm install

npm run dev
```

Abrir:

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

---

## Teste manual da V3

1. Abrir frontend.
2. Enviar mensagem com MockProvider.
3. Confirmar histórico na tela.
4. Marcar `Gostei` em uma resposta.
5. Recarregar a página.
6. Confirmar persistência do histórico e do feedback.
7. Trocar para `Não gostei`.
8. Recarregar a página.
9. Confirmar feedback atualizado.
10. Limpar histórico.
11. Confirmar que o histórico foi apagado.

---

## Obsidian/documentação

Abrir no Obsidian:

```txt
C:\Projetos\pedrocore-ia\docs
```

Arquivos da V3:

```txt
docs/04-comandos/V3_COMANDOS.md
docs/04-comandos/V3_GIT_VERSIONAMENTO.md
docs/06_ERROS_E_CORRECOES.md
docs/08_CHANGELOG.md
docs/09_STATUS_ATUAL.md
docs/10_V3_HISTORICO_E_FEEDBACK.md
```

---

## Terminal 1 — Salvar V3 no Git local

Só execute depois que os testes passarem.

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git add README.md VERSION.md COMANDOS_POWERSHELL.md .gitignore apps/web/src/pages/ChatPage.tsx apps/web/src/styles/global.css apps/web/src/types/chat.ts apps/web/src/utils/chatStorage.ts docs/04-comandos/V3_COMANDOS.md docs/04-comandos/V3_GIT_VERSIONAMENTO.md docs/06_ERROS_E_CORRECOES.md docs/08_CHANGELOG.md docs/09_STATUS_ATUAL.md docs/10_V3_HISTORICO_E_FEEDBACK.md

git status --short

git commit -m "feat: adicionar historico local e feedback das respostas"
```

---

## Terminal 1 — Criar tag da V3

```powershell
cd C:\Projetos\pedrocore-ia

git tag v3.0.0

git log --oneline --decorate -5

git tag
```

---

## Terminal 1 — Conferência final

```powershell
cd C:\Projetos\pedrocore-ia

git status

git log --oneline --decorate -5

git tag

git ls-files | Select-String "\.env"
```

Resultado esperado:

- Working tree clean.
- Tag `v3.0.0` criada.
- Tag `v2.0.0` preservada.
- `.env` real não versionado.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
