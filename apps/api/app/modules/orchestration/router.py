import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.modules.caller_identity.service import caller_identity_service
from app.modules.caller_identity.technical_api import (
    read_api_key,
    AUTH_INVALID_REASON,
    AUTH_MISSING_REASON,
    AUTH_NOT_CONFIGURED_WARNING,
)
from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.contracts.codes import make_warning
from app.modules.orchestration.schemas import OrchestrateResponse
from app.modules.orchestration.service import orchestration_service

router = APIRouter(tags=["Orchestration"])

API_KEY_ENV_VAR = "PEDROCORE_INTERNAL_API_KEY"


def _auth_error(
    error_code: str,
    reason: str,
    correlation_id: str | None = None,
) -> JSONResponse:
    content = {
        "status": "blocked",
        "error_code": error_code,
        "blocked_reason": reason,
        "warning_codes": [error_code],
    }
    if correlation_id is not None:
        content["correlation_id"] = correlation_id
    return JSONResponse(
        status_code=401,
        content=content,
    )


@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(payload: ChatRequest, request: Request):
    configured_key = (os.environ.get(API_KEY_ENV_VAR) or "").strip()
    provided_key = read_api_key(request)
    auth_warnings = []

    if configured_key:
        if provided_key is None:
            return _auth_error(
                codes.INTERNAL_AUTH_MISSING,
                AUTH_MISSING_REASON,
                payload.correlation_id,
            )
        if provided_key != configured_key:
            return _auth_error(
                codes.INTERNAL_AUTH_INVALID,
                AUTH_INVALID_REASON,
                payload.correlation_id,
            )
    elif not caller_identity_service.registry_configured():
        auth_warnings.append(
            make_warning(codes.INTERNAL_AUTH_NOT_CONFIGURED, AUTH_NOT_CONFIGURED_WARNING)
        )

    # Identidade derivada da credencial apresentada; o payload nunca a define.
    resolution = caller_identity_service.resolve(provided_key)
    if resolution.rejected:
        return _auth_error(
            resolution.error_code or codes.CALLER_CREDENTIAL_UNKNOWN,
            resolution.reason or "Credencial não reconhecida pelo Veltrix.",
            payload.correlation_id,
        )

    outcome = await orchestration_service.execute(payload, caller=resolution.context)

    warning_items = auth_warnings + outcome.warning_items

    return OrchestrateResponse(
        status=outcome.status,
        answer=outcome.answer,
        task_type=outcome.task_type,
        origin_system=outcome.origin_system,
        provider_requested=outcome.provider_requested,
        provider_used=outcome.provider_used,
        model=outcome.model,
        mode=outcome.mode,
        fallback_used=outcome.fallback_used,
        safe_mode_blocked=outcome.safe_mode_blocked,
        allow_real_provider=payload.allow_real_provider,
        warning_codes=[item.code for item in warning_items],
        warnings=warning_items,
        task_warnings=[item.message for item in warning_items],
        error_code=outcome.error_code,
        blocked_reason=outcome.blocked_reason,
        correlation_id=outcome.correlation_id,
        idempotency_replayed=outcome.idempotency_replayed,
        elyra=outcome.elyra,
        elyra_multimodal=outcome.elyra_multimodal,
        elyra_learning=outcome.elyra_learning,
        project_id=outcome.project_id,
        task_allowed_for_project=outcome.task_allowed_for_project,
        artifact_count=outcome.artifact_count,
        artifact_types=outcome.artifact_types,
        artifact_warnings=outcome.artifact_warnings,
        qa=outcome.qa_skeleton,
        release_gate=outcome.release_gate,
        visual_qa_analysis=outcome.visual_qa_analysis,
        exploration=outcome.exploration,
        audit=outcome.audit,
        memory_used=outcome.memory_used,
    )
