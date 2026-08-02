# V5.1.9 — Comandos PowerShell

## Objetivo

Aplicar a versão V5.1.9 do PedroCore IA com redesign real do frontend baseado no mockup aprovado e com a logo oficial escolhida.

## Terminal 1 — Conferir base

```powershell
cd C:\Projetos\pedrocore-ia

git status

git log --oneline --decorate -5

git tag

git ls-files | Select-String "\.env"
```

## Terminal 1 — Aplicar pacote

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v51_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v5.1.1.zip" -DestinationPath "C:\Projetos\_pedrocore_v51_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v51_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v51_temp"
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

git commit -m "feat: refazer frontend com redesign aprovado e logo oficial"

git tag -a v5.1.1 -m "PedroCore IA V5.1 approved - redesigned frontend with official logo"
```

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
