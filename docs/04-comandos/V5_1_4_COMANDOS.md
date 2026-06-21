# V5.1.9 — Comandos PowerShell

## Objetivo

Aplicar a correção estrutural de responsividade em notebook e o ajuste do botão Configurações.

## Terminal 1 — Aplicar ZIP

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v514_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v5.1.9-responsivo.zip" -DestinationPath "C:\Projetos\_pedrocore_v514_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v514_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v514_temp"
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

git add -A

git reset docs/.obsidian/ 2>$null

git commit -m "fix: corrigir responsividade estrutural e foco das configuracoes"

git tag -a v5.1.9 -m "PedroCore IA V5.1.9 approved - structural responsiveness and settings focus"
```
