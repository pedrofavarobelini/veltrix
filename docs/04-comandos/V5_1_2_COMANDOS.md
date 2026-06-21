# V5.1.2 — Comandos PowerShell

## Objetivo

Aplicar a revisão de fidelidade visual e responsividade para notebook da tela aprovada do PedroCore IA.

## Terminal 1 — Conferir estado antes

```powershell
cd C:\Projetos\pedrocore-ia

git status

git log --oneline --decorate -5

git tag

git ls-files | Select-String "\.env"
```

## Terminal 1 — Aplicar ZIP

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v512_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v5.1.2-notebook.zip" -DestinationPath "C:\Projetos\_pedrocore_v512_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v512_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v512_temp"
```

## Terminal 2 — Backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv sync

uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 3333
```

## Terminal 3 — Frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm install

npm run dev
```

Abrir:

```txt
http://localhost:5173
```

## Terminal 1 — Teste backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv run pytest
```

## Terminal 3 — Teste frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm run build
```

## Terminal 1 — Commit e tag

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git add -A

git reset docs/.obsidian/ 2>$null

git status --short

git commit -m "fix: ajustar responsividade notebook e fidelidade visual"

git tag -a v5.1.2 -m "PedroCore IA V5.1.2 approved - notebook responsiveness and visual fidelity"
```

## Terminal 1 — Conferência final

```powershell
cd C:\Projetos\pedrocore-ia

git log --oneline --decorate -5

git tag

git status

git ls-files | Select-String "\.env"
```
