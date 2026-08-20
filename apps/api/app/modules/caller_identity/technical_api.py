"""Autorização comum e fail-closed para APIs técnicas operacionais."""

from fastapi import Request
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

API_KEY_HEADER = "X-PedroCore-Api-Key"
AUTH_MISSING_REASON = "Autenticação interna configurada e header X-PedroCore-Api-Key ausente."
AUTH_INVALID_REASON = "Autenticação interna configurada e header X-PedroCore-Api-Key inválido."
AUTH_NOT_CONFIGURED_WARNING = (
    "PEDROCORE_INTERNAL_API_KEY não configurada; API operando "
    "em modo dev/local sem autenticação interna."
)

TECHNICAL_ROLE_REASON = "APIs de inteligência operacional exigem caller com papel technical_tool."
TECHNICAL_PROJECT_REASON = (
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


def authentication_error(error_code: str, reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "status": "blocked",
            "error_code": error_code,
            "blocked_reason": reason,
            "warning_codes": [error_code],
        },
    )


def authorization_error(error_code: str, reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={
            "status": "blocked",
            "error_code": error_code,
            "blocked_reason": reason,
            "warning_codes": [error_code],
        },
    )


def operational_persistence_error(error_code: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "blocked",
            "error_code": error_code,
            "blocked_reason": (
                "Persistência operacional indisponível ou não migrada; "
                "nenhum fallback foi aplicado."
            ),
            "warning_codes": [error_code],
        },
    )


def authorize_technical_request(
    request: Request, project_id: str
) -> tuple[
    JSONResponse | None,
    list[WarningItem],
    AuthenticatedCallerContext | None,
]:
    """Resolve caller e autoriza exatamente um projeto, sempre fail-closed."""
    provided = request.headers.get(API_KEY_HEADER)
    registry_configured = caller_identity_service.registry_configured()
    shared_key_configured = caller_identity_service.shared_key_configured()
    resolution = caller_identity_service.resolve(provided)

    if resolution.rejected:
        error_code = resolution.error_code or codes.CALLER_CREDENTIAL_UNKNOWN
        reason = resolution.reason or "Credencial não reconhecida pelo PedroCore."
        if shared_key_configured and not registry_configured:
            if provided is None:
                error_code, reason = codes.INTERNAL_AUTH_MISSING, AUTH_MISSING_REASON
            else:
                error_code, reason = codes.INTERNAL_AUTH_INVALID, AUTH_INVALID_REASON
        return authentication_error(error_code, reason), [], None

    caller = resolution.context
    if caller is None:
        return (
            authentication_error(
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
                authorization_error(codes.CALLER_ORIGIN_MISMATCH, TECHNICAL_PROJECT_REASON),
                [],
                None,
            )
        if caller.caller_role is not CallerRole.TECHNICAL_TOOL:
            return (
                authorization_error(codes.CALLER_REPORT_ACCESS_NOT_ALLOWED, TECHNICAL_ROLE_REASON),
                [],
                None,
            )
    elif caller.identity_strength is IdentityStrength.AMBIGUOUS:
        if normalized_project != SHARED_OR_UNKNOWN_PROJECT_ID:
            return (
                authorization_error(codes.CALLER_IDENTITY_AMBIGUOUS, LEGACY_PROJECT_REASON),
                [],
                None,
            )
        warnings.append(make_warning(codes.CALLER_IDENTITY_SHARED_CREDENTIAL, LEGACY_WARNING))
    elif caller.identity_strength is IdentityStrength.LOCAL_TRUSTED:
        if caller.environment in {"prod", "production"}:
            return (
                authentication_error(
                    codes.CALLER_CREDENTIAL_MISSING,
                    "Inteligência operacional exige identidade registrada em produção.",
                ),
                [],
                None,
            )
        warnings.append(
            make_warning(codes.INTERNAL_AUTH_NOT_CONFIGURED, AUTH_NOT_CONFIGURED_WARNING)
        )
    else:
        return (
            authorization_error(
                codes.CALLER_IDENTITY_AMBIGUOUS,
                "Força de identidade não autorizada para inteligência operacional.",
            ),
            [],
            None,
        )

    return None, warnings, caller


def validate_producer(caller: AuthenticatedCallerContext, producer: str) -> JSONResponse | None:
    if producer.strip() != caller.credential_id:
        return authorization_error(
            codes.CALLER_REPORT_PRODUCER_MISMATCH,
            PRODUCER_MISMATCH_REASON,
        )
    return None
