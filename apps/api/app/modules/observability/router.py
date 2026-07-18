import ipaddress

from fastapi import APIRouter, HTTPException, Query, Request

from app.modules.observability.gemini_smoke import gemini_smoke_service
from app.modules.observability.schemas import (
    ExecutionListResponse,
    ExecutionRecord,
    GeminiSmokeRequest,
    GeminiSmokeResponse,
    ObservabilityStatusResponse,
)
from app.modules.observability.service import NOTICE, observability_service

router = APIRouter(tags=["Observability"])


def _is_loopback(request: Request) -> bool:
    host = request.client.host if request.client else ""
    if host == "testclient":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host in {"localhost"}


def _require_local_enabled(request: Request) -> None:
    if not _is_loopback(request) or not observability_service.enabled():
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/observability/status", response_model=ObservabilityStatusResponse)
def observability_status(request: Request):
    local = _is_loopback(request)
    enabled = local and observability_service.enabled()
    return ObservabilityStatusResponse(
        enabled=enabled,
        mode=observability_service.mode(),
        max_entries=observability_service.max_entries(),
        notice=NOTICE,
    )


@router.get("/observability/executions", response_model=ExecutionListResponse)
def list_executions(
    request: Request,
    origin: str | None = None,
    task: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    fallback: bool | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    _require_local_enabled(request)
    items = observability_service.list(
        origin=origin,
        task=task,
        status=status,
        provider=provider,
        fallback=fallback,
        limit=limit,
    )
    return ExecutionListResponse(
        enabled=True,
        mode=observability_service.mode(),
        total=len(items),
        items=items,
    )


@router.get(
    "/observability/executions/{execution_id}",
    response_model=ExecutionRecord,
)
def execution_detail(execution_id: str, request: Request):
    _require_local_enabled(request)
    record = observability_service.get(execution_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    return record


@router.post("/observability/gemini-smoke", response_model=GeminiSmokeResponse)
async def gemini_smoke(payload: GeminiSmokeRequest, request: Request):
    if not _is_loopback(request):
        raise HTTPException(status_code=404, detail="Not found")
    if not observability_service.enabled() and observability_service.mode() not in {
        "prod",
        "production",
    }:
        raise HTTPException(status_code=404, detail="Not found")
    return await gemini_smoke_service.execute(payload)
