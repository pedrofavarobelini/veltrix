# V5.1.5 — Comandos PowerShell

## Objetivo

Aplicar a correção pequena da interface: remover o botão Configurações da sidebar e limpar o topo para exibir apenas logo + nome do projeto.

## Terminal 1 — Aplicar ZIP

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v515_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v5.1.5-topo-sidebar.zip" -DestinationPath "C:\Projetos\_pedrocore_v515_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v515_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v515_temp"
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

git commit -m "fix: limpar topo e remover botao configuracoes da sidebar"

git tag -a v5.1.5 -m "Veltrix V5.1.5 approved - clean header and sidebar"
```

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
