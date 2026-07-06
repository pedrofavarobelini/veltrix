# PedroCore IA API

Backend Python + FastAPI do PedroCore IA. Estado atual: core operacional seguro local (`v7.0.0`) com `/api/chat` legado e `/api/orchestrate` operacional.

## Rodar

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
uv sync
uv run pytest
uv run uvicorn app.main:app --reload --port 3333
```

## Rotas

- `GET /`
- `GET /health`
- `POST /api/chat`
- `GET /api/providers`
- `POST /api/orchestrate`
- `GET /docs`

`/api/orchestrate` é o endpoint principal do core operacional. Use `provider=mock` ou `provider=local_qa` para testes seguros. Providers reais são bloqueados por padrão por `allow_real_provider=false`.
