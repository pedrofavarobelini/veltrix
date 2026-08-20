import time

from fastapi import APIRouter, Request
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
from app.modules.report_intelligence.schemas import TechnicalReportInput
from app.modules.report_memory.schemas import (
    ProjectMemorySummaryResponse,
    ReportAnalyzeResponse,
    ReportIngestResponse,
)
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
        return _auth_error(
            codes.CALLER_CREDENTIAL_UNKNOWN,
            "Nenhuma identidade de caller pôde ser resolvida.",
        ), [], None

    normalized_project = project_id.strip().lower()
    warnings: list[WarningItem] = []

    if caller.identity_strength is IdentityStrength.REGISTERED:
        origin_claim = caller_identity_service.validate_origin_claim(
            caller, normalized_project, normalized_project
        )
        if origin_claim.rejected or caller.project_id != normalized_project:
            return _authorization_error(
                codes.CALLER_ORIGIN_MISMATCH, REPORT_PROJECT_REASON
            ), [], None
        if caller.caller_role is not CallerRole.TECHNICAL_TOOL:
            return _authorization_error(
                codes.CALLER_REPORT_ACCESS_NOT_ALLOWED, REPORT_ROLE_REASON
            ), [], None
    elif caller.identity_strength is IdentityStrength.AMBIGUOUS:
        if normalized_project != SHARED_OR_UNKNOWN_PROJECT_ID:
            return _authorization_error(
                codes.CALLER_IDENTITY_AMBIGUOUS, LEGACY_PROJECT_REASON
            ), [], None
        warnings.append(
            make_warning(codes.CALLER_IDENTITY_SHARED_CREDENTIAL, LEGACY_WARNING)
        )
    elif caller.identity_strength is IdentityStrength.LOCAL_TRUSTED:
        # Retrocompatibilidade dev/local existente. Em produção, a ausência de
        # identidade registrada é tratada como credencial ausente.
        if caller.environment in {"prod", "production"}:
            return _auth_error(
                codes.CALLER_CREDENTIAL_MISSING,
                "Report Memory exige identidade registrada em produção.",
            ), [], None
        warnings.append(
            make_warning(
                codes.INTERNAL_AUTH_NOT_CONFIGURED, AUTH_NOT_CONFIGURED_WARNING
            )
        )
    else:
        return _authorization_error(
            codes.CALLER_IDENTITY_AMBIGUOUS,
            "Força de identidade não autorizada para Report Memory.",
        ), [], None

    return None, warnings, caller


@router.post("/reports/analyze", response_model=ReportAnalyzeResponse)
def analyze_report(payload: TechnicalReportInput, request: Request):
    """Analisa um relatório técnico sem persistir nada."""
    started = time.perf_counter()
    error, warnings, caller = _check_auth(request, payload.project_id)
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
