# V5.1.8 — Comandos PowerShell

## Objetivo

Aplicar correção mínima: esconder os 3 ícones do topo interno, preservando exatamente o layout e a responsividade da V5.1.7.

## Terminal 1 — Aplicar ZIP

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v518_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v5.1.8-so-remover-3-icones.zip" -DestinationPath "C:\Projetos\_pedrocore_v518_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v518_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v518_temp"
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

git commit -m "fix: esconder 3 icones do topo interno"

git tag -a v5.1.8 -m "PedroCore IA V5.1.8 approved - hide internal header icons"
```

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
