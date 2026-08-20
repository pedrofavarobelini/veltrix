import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.chat.router import router as chat_router
from app.modules.interaction_outcomes.router import router as interaction_outcomes_router
from app.modules.observability.router import router as observability_router
from app.modules.operational_memory.router import router as operational_memory_router
from app.modules.retrieval.router import router as retrieval_router
from app.modules.safe_reuse.router import router as safe_reuse_router
from app.modules.orchestration.router import router as orchestration_router
from app.modules.report_memory.router import router as report_memory_router

app = FastAPI(
    title="PedroCore IA",
    version="0.2.0",
    description="API multi-provider de IA para testar respostas, contexto e qualidade.",
)

cors_origins = [
    item.strip().rstrip("/")
    for item in (
        os.environ.get("PEDROCORE_CORS_ORIGINS") or "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if item.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "PedroCore IA",
        "version": "0.2.0",
        "message": "API multi-provider online.",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "PedroCore IA",
        "version": "0.2.0",
    }


app.include_router(chat_router, prefix="/api")
app.include_router(orchestration_router, prefix="/api")
app.include_router(report_memory_router, prefix="/api")
app.include_router(interaction_outcomes_router, prefix="/api")
app.include_router(operational_memory_router, prefix="/api")
app.include_router(retrieval_router, prefix="/api")
app.include_router(safe_reuse_router, prefix="/api")
app.include_router(observability_router, prefix="/api")
