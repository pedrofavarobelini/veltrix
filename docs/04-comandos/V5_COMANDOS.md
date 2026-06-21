# V5 — Comandos PowerShell

Versão atual: V5.0.0 — Configurações de provider pela interface e logo oficial

Local oficial:

```txt
C:\Projetos\pedrocore-ia
```

## Terminal 1 — Conferir Git antes da V5

```powershell
cd C:\Projetos\pedrocore-ia

git status

git log --oneline --decorate -5

git tag

git ls-files | Select-String "\.env"
```

Esperado:

```txt
working tree clean
v4.0.0 no último commit
v3.0.0 preservada
v2.0.0 preservada
apps/api/.env.example apenas
```

## Aplicar ZIP da V5

Coloque em Downloads:

```txt
pedrocore-ia-v5.0.0.zip
```

Depois rode:

```powershell
cd C:\Projetos

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v5_temp" -ErrorAction SilentlyContinue

Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v5.0.0.zip" -DestinationPath "C:\Projetos\_pedrocore_v5_temp" -Force

Get-ChildItem "C:\Projetos\_pedrocore_v5_temp\pedrocore-ia" -Force | Copy-Item -Destination "C:\Projetos\pedrocore-ia" -Recurse -Force

Remove-Item -Recurse -Force "C:\Projetos\_pedrocore_v5_temp"
```

Esse comando preserva:

```txt
.git
apps/api/.env
histórico Git
tags anteriores
```

## Terminal 2 — Rodar backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv sync

uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 3333
```

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

## Terminal 1 — Testar backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api

uv run pytest
```

Esperado:

```txt
7 passed
```

## Terminal 3 — Testar frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web

npm run build
```

## Teste manual obrigatório da V5

1. Abrir o frontend.
2. Conferir se a logo oficial aparece na sidebar.
3. Conferir se o avatar das respostas da IA usa a logo oficial.
4. Conferir se o favicon do navegador mudou.
5. Abrir o painel de providers.
6. Conferir cards de Mock, Gemini, OpenAI, Claude, DeepSeek e Grok/xAI.
7. Selecionar provider.
8. Alterar modelo, modo e prompt base.
9. Salvar configuração local.
10. Recarregar a página.
11. Confirmar persistência das preferências.
12. Enviar mensagem com MockProvider.
13. Enviar mensagem com GeminiProvider, se a chave estiver configurada no `.env`.
14. Confirmar que o histórico da V3/V4 não foi perdido.

## Commit e tag da V5

Só depois de testar e aprovar localmente.

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git add -A

git reset docs/.obsidian/ 2>$null

git status --short

git commit -m "feat: adicionar configuracoes de provider e logo oficial"

git tag -a v5.0.0 -m "PedroCore IA V5 approved - provider settings and official logo"
```

## Conferência final

```powershell
cd C:\Projetos\pedrocore-ia

git log --oneline --decorate -5

git tag

git status

git ls-files | Select-String "\.env"
```

Resultado esperado:

```txt
v5.0.0 no último commit
v4.0.0 preservada
v3.0.0 preservada
v2.0.0 preservada
working tree clean
apps/api/.env.example apenas
```

## Documentação principal

```txt
docs/04-comandos/V5_COMANDOS.md
docs/12_V5_CONFIG_PROVIDER.md
docs/13_V5_IDENTIDADE_VISUAL.md
docs/09_STATUS_ATUAL.md
VERSION.md
```
