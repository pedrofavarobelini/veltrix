from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.chat.router import router as chat_router
from app.modules.orchestration.router import router as orchestration_router

app = FastAPI(
    title="PedroCore IA",
    version="0.2.0",
    description="API multi-provider de IA para testar respostas, contexto e qualidade.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
