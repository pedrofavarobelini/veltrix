# Veltrix — Comandos PowerShell V1

## Versão atual

```txt
Veltrix — V1
Status: base inicial funcional
Local correto: C:\Projetos\pedrocore-ia
```

## Parte 1 — Conferir a pasta Projetos

```powershell
cd C:\
```

```powershell
mkdir Projetos -ErrorAction SilentlyContinue
```

```powershell
cd C:\Projetos
```

```powershell
dir
```

Resultado esperado: o FinGuard deve aparecer como uma pasta dentro de `C:\Projetos`.

## Parte 2 — Extrair o ZIP

O ZIP deve ser extraído diretamente dentro de `C:\Projetos`.

Se o ZIP estiver em Downloads:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\pedrocore-ia-v1.zip" -DestinationPath "C:\Projetos" -Force
```

Depois confira:

```powershell
cd C:\Projetos
```

```powershell
dir
```

Resultado esperado:

```txt
FinGuard
pedrocore-ia
```

## Parte 3 — Conferir estrutura do projeto

```powershell
cd C:\Projetos\pedrocore-ia
```

```powershell
dir
```

Resultado esperado:

```txt
apps
docs
README.md
VERSION.md
COMANDOS_POWERSHELL.md
```

## Parte 4 — Verificar ferramentas

Rode um por vez:

```powershell
python --version
```

```powershell
node -v
```

```powershell
npm -v
```

```powershell
uv --version
```

Se `uv` não existir:

```powershell
pip install uv
```

Depois confirme:

```powershell
uv --version
```

## Terminal 1 — Backend

Abra o PowerShell 1:

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
```

```powershell
uv sync
```

```powershell
uv run uvicorn app.main:app --reload --port 3333
```

Deixe esse terminal aberto.

Teste no navegador:

```txt
http://localhost:3333/health
```

Resultado esperado:

```json
{
  "status": "ok",
  "service": "Veltrix",
  "version": "0.1.0"
}
```

Swagger:

```txt
http://localhost:3333/docs
```

## Terminal 2 — Frontend

Abra outro PowerShell:

```powershell
cd C:\Projetos\pedrocore-ia\apps\web
```

```powershell
npm install
```

```powershell
npm run dev
```

Abra no navegador:

```txt
http://localhost:5173
```

## Teste da V1

Digite no chat:

```txt
Explique o que é FastAPI nesse projeto.
```

Resultado esperado: resposta do Veltrix usando MockProvider.

## Próximas versões

```txt
V1 — Chat simples + API mock — atual
V2 — Integração real com Gemini — próxima
V3 — Histórico simples + gostei/não gostei salvo — pendente
V4 — Prompts por modo — pendente
V5 — API interna para conexão com FinGuard — pendente
V6 — PostgreSQL + logs — pendente
V7 — RAG/memória com documentos — pendente
V8 — Multi-provider — pendente
V9 — Deploy/documentação final — pendente
```

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
