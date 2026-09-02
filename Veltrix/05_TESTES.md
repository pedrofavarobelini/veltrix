# Veltrix — Testes da V1.0.1

## Testes esperados

### Backend

```powershell
cd C:\Projetos\pedrocore-ia\apps\api
uv sync
uv run pytest
uv run uvicorn app.main:app --reload --port 3333
```

Esperado:

```txt
3 passed
```

Rotas:

```txt
http://localhost:3333/
http://localhost:3333/health
http://localhost:3333/docs
```

### Frontend

```powershell
cd C:\Projetos\pedrocore-ia\apps\web
npm install
npm run dev
```

Abrir:

```txt
http://localhost:5173
```

## Teste de interface

Enviar:

```txt
Explique o que é FastAPI nesse projeto.
```

Validar:

- Resposta aparece.
- Copiar mostra toast.
- Gostei mostra toast.
- Não gostei mostra toast.
- Refazer mostra toast.
- Config abre painel.
- Fechar mostra toast.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_VELTRIX]]
