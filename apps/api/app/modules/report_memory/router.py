import time

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.modules.caller_identity.technical_api import (
    authorize_technical_request as _check_auth,
    operational_persistence_error,
    validate_producer as _check_producer,
)
from app.modules.contracts import codes
from app.modules.contracts.codes import make_warning
from app.modules.observability.service import observability_service
from app.modules.report_intelligence.schemas import (
    IntelligenceReportEnvelopeV2,
    TechnicalReportInput,
)
from app.modules.report_intelligence.service import report_intelligence_service
from app.modules.report_memory.schemas import (
    ProjectMemorySummaryResponse,
    ReportMemoryDeleteResponse,
    ReportMemoryPageResponse,
    ReportAnalyzeResponse,
    ReportAnalyzeV2Response,
    ReportIngestResponse,
    ReportIngestV2Response,
)
from app.modules.report_memory.repository import ReportMemoryRepositoryError
from app.modules.report_memory.service import report_memory_service

# Rotas de memória técnica (PEDROCORE-REPORT-MEMORY-01).
# Reutiliza a mesma Caller Identity de /api/orchestrate. Nenhuma rota lê
# path/arquivo: relatórios chegam exclusivamente por payload. O project_id do
# payload é uma alegação e nunca uma identidade soberana.

router = APIRouter(tags=["Report Memory"])


def _persistence_error() -> JSONResponse:
    return operational_persistence_error(codes.REPORT_PERSISTENCE_UNAVAILABLE)


@router.post("/reports/analyze", response_model=ReportAnalyzeResponse)
def analyze_report(payload: TechnicalReportInput, request: Request):
    """Analisa um relatório técnico sem persistir nada."""
    started = time.perf_counter()
    error, warnings, caller = _check_auth(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None

    envelope = report_intelligence_service.adapt_v1(payload, caller)
    normalized_v2, signals, evaluation = report_memory_service.analyze_envelope(envelope)
    normalized = report_intelligence_service.technical_view(normalized_v2)
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
        caller=caller,
    )
    return response


@router.post("/reports/ingest", response_model=ReportIngestResponse)
def ingest_report(payload: TechnicalReportInput, request: Request):
    """Ingere um relatório na memória técnica (se habilitada)."""
    started = time.perf_counter()
    error, warnings, caller = _check_auth(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None

    envelope = report_intelligence_service.adapt_v1(payload, caller)
    try:
        entry, snapshot, signals, evaluation, ingest_warnings, duplicate = (
            report_memory_service.ingest_envelope(envelope)
        )
    except ReportMemoryRepositoryError:
        return _persistence_error()
    warnings.extend(ingest_warnings)

    response = ReportIngestResponse(
        status="duplicate" if duplicate else ("ok" if entry is not None else "disabled"),
        stored=entry is not None and not duplicate,
        duplicate=duplicate,
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
        caller=caller,
    )
    return response


@router.post("/reports/v2/analyze", response_model=ReportAnalyzeV2Response)
def analyze_report_v2(payload: IntelligenceReportEnvelopeV2, request: Request):
    """Analisa Common Envelope V2 sem persistência ou interpretação de versão futura."""
    started = time.perf_counter()
    error, warnings, caller = _check_auth(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = _check_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error

    normalized, signals, evaluation = report_memory_service.analyze_envelope(payload)
    warnings.append(
        make_warning(
            codes.REPORT_MEMORY_IS_NOT_TRAINING,
            "Relatórios V2 não treinam IA; esta análise gera apenas sinais.",
        )
    )
    response = ReportAnalyzeV2Response(
        report=normalized,
        signals=signals,
        evaluation=evaluation,
        warnings=warnings,
    )
    observability_service.record_report(
        task="report_v2_analysis",
        payload=normalized,
        response=response,
        duration_ms=(time.perf_counter() - started) * 1_000,
        caller=caller,
    )
    return response


@router.post("/reports/v2/ingest", response_model=ReportIngestV2Response)
def ingest_report_v2(payload: IntelligenceReportEnvelopeV2, request: Request):
    """Ingere envelope V2 com isolamento e idempotência por projeto/report_id."""
    started = time.perf_counter()
    error, warnings, caller = _check_auth(request, payload.project_id)
    if error is not None:
        return error
    assert caller is not None
    producer_error = _check_producer(caller, payload.producer)
    if producer_error is not None:
        return producer_error

    try:
        entry, snapshot, signals, evaluation, ingest_warnings, duplicate = (
            report_memory_service.ingest_envelope(payload)
        )
    except ReportMemoryRepositoryError:
        return _persistence_error()
    warnings.extend(ingest_warnings)
    response = ReportIngestV2Response(
        status="duplicate" if duplicate else ("ok" if entry is not None else "disabled"),
        stored=entry is not None and not duplicate,
        duplicate=duplicate,
        report_id=(entry.report_id or payload.report_id.strip())
        if entry is not None
        else payload.report_id.strip(),
        memory_id=entry.memory_id if entry is not None else None,
        snapshot=snapshot,
        signals=signals,
        evaluation=evaluation,
        warnings=warnings,
    )
    observability_service.record_report(
        task="report_v2_ingestion",
        payload=payload,
        response=response,
        duration_ms=(time.perf_counter() - started) * 1_000,
        caller=caller,
    )
    return response


@router.get(
    "/project-memory/{project_id}/summary",
    response_model=ProjectMemorySummaryResponse,
)
def project_memory_summary(project_id: str, request: Request):
    """Snapshot agregado da memória técnica do projeto — sem ler repositório."""
    error, warnings, _caller = _check_auth(request, project_id)
    if error is not None:
        return error

    if not report_memory_service.enabled():
        warnings.append(
            make_warning(
                codes.REPORT_MEMORY_DISABLED,
                "Memória técnica desabilitada; nenhum snapshot disponível.",
            )
        )
        return ProjectMemorySummaryResponse(status="disabled", snapshot=None, warnings=warnings)

    try:
        snapshot = report_memory_service.snapshot(project_id)
    except ReportMemoryRepositoryError:
        return _persistence_error()
    if snapshot is None:
        warnings.append(
            make_warning(
                codes.REPORT_MEMORY_EMPTY,
                "Memória técnica sem registros para este projeto.",
            )
        )
    return ProjectMemorySummaryResponse(status="ok", snapshot=snapshot, warnings=warnings)


@router.get(
    "/project-memory/{project_id}/reports",
    response_model=ReportMemoryPageResponse,
)
def project_memory_reports(
    project_id: str,
    request: Request,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Consulta paginada; o limite de 50 do modo local não limita PostgreSQL."""
    error, warnings, _caller = _check_auth(request, project_id)
    if error is not None:
        return error
    if not report_memory_service.enabled():
        return ReportMemoryPageResponse(
            status="disabled",
            project_id=project_id.strip().lower(),
            limit=limit,
            offset=offset,
            warnings=warnings,
        )
    try:
        items, total = report_memory_service.page(project_id, limit=limit, offset=offset)
    except ReportMemoryRepositoryError:
        return _persistence_error()
    return ReportMemoryPageResponse(
        project_id=project_id.strip().lower(),
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        warnings=warnings,
    )


@router.delete(
    "/project-memory/{project_id}",
    response_model=ReportMemoryDeleteResponse,
)
def delete_project_memory(project_id: str, request: Request):
    """Deleção explícita e isolada para privacy/retention; nunca em lote global."""
    error, warnings, _caller = _check_auth(request, project_id)
    if error is not None:
        return error
    try:
        deleted = report_memory_service.delete_project(project_id)
    except ReportMemoryRepositoryError:
        return _persistence_error()
    return ReportMemoryDeleteResponse(
        project_id=project_id.strip().lower(),
        deleted=deleted,
        warnings=warnings,
    )
