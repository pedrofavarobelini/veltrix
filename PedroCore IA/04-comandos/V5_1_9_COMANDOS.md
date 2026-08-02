# V5.1.9 — Comandos PowerShell

## Objetivo

Aplicar a correção definitiva dos ícones/círculos residuais do topo interno.

## Terminal 1 — Aplicar ZIP

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v519_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v5.1.9-sem-icones-definitivo-revisado.zip" -DestinationPath "C:\Projetos\_pedrocore_v519_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v519_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v519_temp"
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

git commit -m "fix: remover definitivamente icones do topo interno"

git tag -a v5.1.9 -m "PedroCore IA V5.1.9 approved - remove internal header icons definitively"
```

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
