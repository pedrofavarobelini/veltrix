import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.contracts.codes import make_warning
from app.modules.orchestration.schemas import OrchestrateResponse
from app.modules.orchestration.service import orchestration_service

router = APIRouter(tags=["Orchestration"])

API_KEY_HEADER = "X-PedroCore-Api-Key"
API_KEY_ENV_VAR = "PEDROCORE_INTERNAL_API_KEY"

AUTH_MISSING_REASON = (
    "Autenticação interna configurada e header X-PedroCore-Api-Key ausente."
)
AUTH_INVALID_REASON = (
    "Autenticação interna configurada e header X-PedroCore-Api-Key inválido."
)
AUTH_NOT_CONFIGURED_WARNING = (
    "PEDROCORE_INTERNAL_API_KEY não configurada; /api/orchestrate operando "
    "em modo dev/local sem autenticação interna."
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


@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(payload: ChatRequest, request: Request):
    configured_key = (os.environ.get(API_KEY_ENV_VAR) or "").strip()
    auth_warnings = []

    if configured_key:
        provided_key = request.headers.get(API_KEY_HEADER)
        if provided_key is None:
            return _auth_error(codes.INTERNAL_AUTH_MISSING, AUTH_MISSING_REASON)
        if provided_key != configured_key:
            return _auth_error(codes.INTERNAL_AUTH_INVALID, AUTH_INVALID_REASON)
    else:
        auth_warnings.append(
            make_warning(codes.INTERNAL_AUTH_NOT_CONFIGURED, AUTH_NOT_CONFIGURED_WARNING)
        )

    outcome = await orchestration_service.execute(payload)

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
    )
