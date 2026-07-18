import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.modules.contracts import codes
from app.modules.contracts.codes import WarningItem, make_warning
from app.modules.orchestration.router import (
    API_KEY_ENV_VAR,
    API_KEY_HEADER,
    AUTH_INVALID_REASON,
    AUTH_MISSING_REASON,
    AUTH_NOT_CONFIGURED_WARNING,
)
from app.modules.observability.service import observability_service
from app.modules.report_intelligence.schemas import TechnicalReportInput
from app.modules.report_memory.schemas import (
    ProjectMemorySummaryResponse,
    ReportAnalyzeResponse,
    ReportIngestResponse,
)
from app.modules.report_memory.service import report_memory_service

# Rotas de memória técnica (PEDROCORE-REPORT-MEMORY-01).
# Mesma autenticação interna opcional do /api/orchestrate. Nenhuma rota lê
# path/arquivo: relatórios chegam exclusivamente por payload.

router = APIRouter(tags=["Report Memory"])


def _auth_error(error_code: str, reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "status": "blocked",
            "error_code": error_code,
            "blocked_reason": reason,
            "warning_codes": [error_code],
        },
    )


def _check_auth(request: Request) -> tuple[JSONResponse | None, list[WarningItem]]:
    configured_key = (os.environ.get(API_KEY_ENV_VAR) or "").strip()
    if configured_key:
        provided = request.headers.get(API_KEY_HEADER)
        if provided is None:
            return _auth_error(codes.INTERNAL_AUTH_MISSING, AUTH_MISSING_REASON), []
        if provided != configured_key:
            return _auth_error(codes.INTERNAL_AUTH_INVALID, AUTH_INVALID_REASON), []
        return None, []
    return None, [
        make_warning(codes.INTERNAL_AUTH_NOT_CONFIGURED, AUTH_NOT_CONFIGURED_WARNING)
    ]


@router.post("/reports/analyze", response_model=ReportAnalyzeResponse)
def analyze_report(payload: TechnicalReportInput, request: Request):
    """Analisa um relatório técnico sem persistir nada."""
    started = time.perf_counter()
    error, warnings = _check_auth(request)
    if error is not None:
        return error

    normalized, signals, evaluation = report_memory_service.analyze(payload)
    warnings.append(
        make_warning(
            codes.REPORT_MEMORY_IS_NOT_TRAINING,
            "Relatórios não treinam IA; esta análise gera apenas sinais.",
        )
    )
    response = ReportAnalyzeResponse(
        status="ok",
        report=normalized,
        signals=signals,
        evaluation=evaluation,
        warnings=warnings,
    )
    observability_service.record_report(
        task="qa_report_analysis",
        payload=payload,
        response=response,
        duration_ms=(time.perf_counter() - started) * 1_000,
    )
    return response


@router.post("/reports/ingest", response_model=ReportIngestResponse)
def ingest_report(payload: TechnicalReportInput, request: Request):
    """Ingere um relatório na memória técnica (se habilitada)."""
    started = time.perf_counter()
    error, warnings = _check_auth(request)
    if error is not None:
        return error

    entry, snapshot, signals, evaluation, ingest_warnings = (
        report_memory_service.ingest(payload)
    )
    warnings.extend(ingest_warnings)

    response = ReportIngestResponse(
        status="ok" if entry is not None else "disabled",
        stored=entry is not None,
        memory_id=entry.memory_id if entry is not None else None,
        snapshot=snapshot,
        signals=signals,
        evaluation=evaluation,
        warnings=warnings,
    )
    observability_service.record_report(
        task="report_ingestion",
        payload=payload,
        response=response,
        duration_ms=(time.perf_counter() - started) * 1_000,
    )
    return response


@router.get(
    "/project-memory/{project_id}/summary",
    response_model=ProjectMemorySummaryResponse,
)
def project_memory_summary(project_id: str, request: Request):
    """Snapshot agregado da memória técnica do projeto — sem ler repositório."""
    error, warnings = _check_auth(request)
    if error is not None:
        return error

    if not report_memory_service.enabled():
        warnings.append(
            make_warning(
                codes.REPORT_MEMORY_DISABLED,
                "Memória técnica desabilitada; nenhum snapshot disponível.",
            )
        )
        return ProjectMemorySummaryResponse(
            status="disabled", snapshot=None, warnings=warnings
        )

    snapshot = report_memory_service.snapshot(project_id)
    if snapshot is None:
        warnings.append(
            make_warning(
                codes.REPORT_MEMORY_EMPTY,
                "Memória técnica sem registros para este projeto.",
            )
        )
    return ProjectMemorySummaryResponse(
        status="ok", snapshot=snapshot, warnings=warnings
    )
