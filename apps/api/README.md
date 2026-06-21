# PedroCore IA API

Backend Python + FastAPI da V1.0.1.

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
- `GET /docs`
