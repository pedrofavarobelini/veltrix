import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.modules.chat.router import router as chat_router
from app.modules.interaction_outcomes.router import router as interaction_outcomes_router
from app.modules.observability.router import router as observability_router
from app.modules.operational_memory.router import router as operational_memory_router
from app.modules.retrieval.router import router as retrieval_router
from app.modules.risk_engine.router import router as risk_engine_router
from app.modules.safe_reuse.router import router as safe_reuse_router
from app.modules.training_data.router import router as training_data_router
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


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error(_request: Request, exc: RequestValidationError):
    """Keep the 422 contract without echoing rejected payloads or validator context."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "loc": list(item.get("loc", ())),
                    "msg": str(item.get("msg", "Invalid input.")),
                    "type": str(item.get("type", "value_error")),
                }
                for item in exc.errors()
            ]
        },
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
app.include_router(risk_engine_router, prefix="/api")
app.include_router(safe_reuse_router, prefix="/api")
app.include_router(observability_router, prefix="/api")
app.include_router(training_data_router, prefix="/api")
