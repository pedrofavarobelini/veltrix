# V5.1.9 — Comandos PowerShell

## Objetivo

Aplicar a revisão de CSS no topo, bloco de conversas recentes e logos/ícones dos providers.

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

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v513_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v5.1.9-css-logos-revisado.zip" -DestinationPath "C:\Projetos\_pedrocore_v513_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v513_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v513_temp"
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

## Testes

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv run pytest
```

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm run build
```

## Git

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git add -A

git reset docs/.obsidian/ 2>$null

git status --short

git commit -m "fix: corrigir topo conversas recentes e logos dos providers"

git tag -a v5.1.9 -m "PedroCore IA V5.1.9 approved - CSS fixes and provider logos"
```

## Conferência final

```powershell
cd C:\Projetos\pedrocore-ia

git log --oneline --decorate -5

git tag

git status

git ls-files | Select-String "\.env"
```
