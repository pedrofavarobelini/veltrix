import time

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from app.modules.caller_identity.schemas import (
    SHARED_OR_UNKNOWN_PROJECT_ID,
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.caller_identity.service import caller_identity_service
from app.modules.contracts import codes
from app.modules.contracts.codes import WarningItem, make_warning
from app.modules.orchestration.router import (
    API_KEY_HEADER,
    AUTH_INVALID_REASON,
    AUTH_MISSING_REASON,
    AUTH_NOT_CONFIGURED_WARNING,
)
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

REPORT_ROLE_REASON = (
    "Rotas de Report Memory exigem caller com papel technical_tool; "
    "consumidor comum não pode analisar, gravar ou consultar memória técnica."
)
REPORT_PROJECT_REASON = (
    "project_id solicitado não corresponde ao projeto autenticado da credencial."
)
LEGACY_PROJECT_REASON = (
    "Credencial compartilhada LEGACY não prova projeto e só pode usar o namespace "
    f"{SHARED_OR_UNKNOWN_PROJECT_ID!r}; projetos concretos exigem credencial registrada."
)
LEGACY_WARNING = (
    "Fluxo LEGACY com credencial compartilhada: autenticado sem identidade de projeto; "
    f"acesso restrito ao namespace {SHARED_OR_UNKNOWN_PROJECT_ID!r}."
)
PRODUCER_MISMATCH_REASON = (
    "producer declarado não corresponde ao credential_id autenticado; "
    "provenance nunca pode ser definida pelo payload."
)


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


def _authorization_error(error_code: str, reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "status": "blocked",
            "error_code": error_code,
            "blocked_reason": reason,
            "warning_codes": [error_code],
        },
    )


def _persistence_error() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "blocked",
            "error_code": codes.REPORT_PERSISTENCE_UNAVAILABLE,
            "blocked_reason": (
                "Persistência operacional indisponível ou não migrada; "
                "nenhum fallback foi aplicado."
            ),
            "warning_codes": [codes.REPORT_PERSISTENCE_UNAVAILABLE],
        },
    )


def _check_auth(
    request: Request, project_id: str
) -> tuple[
    JSONResponse | None,
    list[WarningItem],
    AuthenticatedCallerContext | None,
]:
    """Resolve caller e autoriza exatamente um projeto, sempre fail-closed.

    `credential_id` é o producer interno da requisição V1. Papel e ambiente
    também vêm da identidade; nenhum desses valores pode ser definido pelo
    payload de Report Memory.
    """
    provided = request.headers.get(API_KEY_HEADER)
    registry_configured = caller_identity_service.registry_configured()
    shared_key_configured = caller_identity_service.shared_key_configured()
    resolution = caller_identity_service.resolve(provided)

    if resolution.rejected:
        error_code = resolution.error_code or codes.CALLER_CREDENTIAL_UNKNOWN
        reason = resolution.reason or "Credencial não reconhecida pelo PedroCore."
        # Compatibilidade do contrato HTTP histórico da chave interna.
        if shared_key_configured and not registry_configured:
            if provided is None:
                error_code, reason = codes.INTERNAL_AUTH_MISSING, AUTH_MISSING_REASON
            else:
                error_code, reason = codes.INTERNAL_AUTH_INVALID, AUTH_INVALID_REASON
        return _auth_error(error_code, reason), [], None

    caller = resolution.context
    if caller is None:
        return (
            _auth_error(
                codes.CALLER_CREDENTIAL_UNKNOWN,
                "Nenhuma identidade de caller pôde ser resolvida.",
            ),
            [],
            None,
        )

    normalized_project = project_id.strip().lower()
    warnings: list[WarningItem] = []

    if caller.identity_strength is IdentityStrength.REGISTERED:
        origin_claim = caller_identity_service.validate_origin_claim(
            caller, normalized_project, normalized_project
        )
        if origin_claim.rejected or caller.project_id != normalized_project:
            return (
                _authorization_error(codes.CALLER_ORIGIN_MISMATCH, REPORT_PROJECT_REASON),
                [],
                None,
            )
        if caller.caller_role is not CallerRole.TECHNICAL_TOOL:
            return (
                _authorization_error(codes.CALLER_REPORT_ACCESS_NOT_ALLOWED, REPORT_ROLE_REASON),
                [],
                None,
            )
    elif caller.identity_strength is IdentityStrength.AMBIGUOUS:
        if normalized_project != SHARED_OR_UNKNOWN_PROJECT_ID:
            return (
                _authorization_error(codes.CALLER_IDENTITY_AMBIGUOUS, LEGACY_PROJECT_REASON),
                [],
                None,
            )
        warnings.append(make_warning(codes.CALLER_IDENTITY_SHARED_CREDENTIAL, LEGACY_WARNING))
    elif caller.identity_strength is IdentityStrength.LOCAL_TRUSTED:
        # Retrocompatibilidade dev/local existente. Em produção, a ausência de
        # identidade registrada é tratada como credencial ausente.
        if caller.environment in {"prod", "production"}:
            return (
                _auth_error(
                    codes.CALLER_CREDENTIAL_MISSING,
                    "Report Memory exige identidade registrada em produção.",
                ),
                [],
                None,
            )
        warnings.append(
            make_warning(codes.INTERNAL_AUTH_NOT_CONFIGURED, AUTH_NOT_CONFIGURED_WARNING)
        )
    else:
        return (
            _authorization_error(
                codes.CALLER_IDENTITY_AMBIGUOUS,
                "Força de identidade não autorizada para Report Memory.",
            ),
            [],
            None,
        )

    return None, warnings, caller


def _check_producer(caller: AuthenticatedCallerContext, producer: str) -> JSONResponse | None:
    if producer.strip() != caller.credential_id:
        return _authorization_error(
            codes.CALLER_REPORT_PRODUCER_MISMATCH,
            PRODUCER_MISMATCH_REASON,
        )
    return None


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
