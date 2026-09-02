# Veltrix V2 — Comandos PowerShell

## Local correto

```powershell
cd C:\Projetos\pedrocore-ia
```

## Terminal 1 — Backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
```

```powershell
uv sync
```

```powershell
uv run pytest
```

```powershell
uv run uvicorn app.main:app --reload --port 3333
```

Não feche esse terminal.

## Testes do backend no navegador

```txt
http://localhost:3333/
http://localhost:3333/health
http://localhost:3333/docs
http://localhost:3333/api/providers
```

## Terminal 2 — Frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web
```

```powershell
npm install
```

```powershell
npm run build
```

```powershell
npm run dev
```

Abra:

```txt
http://localhost:5173
```

## Terminal 3 — Teste direto da API

### Health

```powershell
Invoke-RestMethod -Uri "http://localhost:3333/health" -Method GET
```

### Providers

```powershell
Invoke-RestMethod -Uri "http://localhost:3333/api/providers" -Method GET
```

### Mock

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:3333/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"message":"Teste com Mock","mode":"tecnico","provider":"mock","model":"mock-v1","system_prompt":"Você é o Veltrix."}'
```

### Gemini

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:3333/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"message":"Explique FastAPI em poucas linhas.","mode":"tecnico","provider":"gemini","model":"gemini-3.5-flash","system_prompt":"Você é o Veltrix."}'
```

Se a chave não estiver configurada, o sistema deve responder com fallback do MockProvider.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
