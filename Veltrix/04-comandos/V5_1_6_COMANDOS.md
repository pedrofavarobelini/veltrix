# V5.1.9 — Comandos PowerShell

## Objetivo

Aplicar a correção que preserva a responsividade estrutural da V5.1.4 e remove apenas o botão Configurações da sidebar e os textos quebrados do topo.

## Terminal 1 — Aplicar ZIP

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v516_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v5.1.9-responsivo-topo.zip" -DestinationPath "C:\Projetos\_pedrocore_v516_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v516_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v516_temp"
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

git commit -m "fix: preservar responsividade e limpar topo sidebar"

git tag -a v5.1.9 -m "Veltrix V5.1.9 approved - responsive layout with clean header"
```

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
