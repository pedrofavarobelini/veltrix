"""Resolução de identidade do caller (MULTI-PROVIDER-SAFE-EVOLUTION, Etapa 2).

Ordem soberana da identidade:

    credencial autenticada
    → registro seguro de caller
    → project_id
    → caller_role
    → environment

`origin_system` do payload continua aceito por compatibilidade, mas apenas
como alegação validada. Divergência entre a origem declarada e a identidade
autenticada é REJEITADA — nunca corrigida silenciosamente.

Limitação conhecida e registrada: enquanto existir apenas uma API key global
(`PEDROCORE_INTERNAL_API_KEY`), a credencial não distingue projetos. Nesse
caso a identidade é marcada como compartilhada (`shared_credential=True`,
validação de origem `not_enforced`) e o isolamento operacional entre projetos
depende do provisionamento de credenciais distintas via
`PEDROCORE_CALLER_REGISTRY`.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from app.core.config import settings
from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerResolution,
    CallerRestrictionResult,
    CallerRole,
    OriginClaimResult,
    OriginValidation,
)
from app.modules.contracts import codes

FLAG_CALLER_REGISTRY = "PEDROCORE_CALLER_REGISTRY"
FLAG_INTERNAL_API_KEY = "PEDROCORE_INTERNAL_API_KEY"
FLAG_INTERNAL_CREDENTIAL_ID = "PEDROCORE_INTERNAL_CREDENTIAL_ID"

SHARED_CREDENTIAL_ID = "internal-shared"
LOCAL_CREDENTIAL_ID = "local-unauthenticated"

FINGERPRINT_PREFIX = "fp"
FINGERPRINT_CHARS = 12

# Seleções que um consumidor comum pode declarar: nenhuma delas escolhe um
# provider externo real. Provider real só chega por `auto` + política.
COMMON_CONSUMER_ALLOWED_SELECTIONS = frozenset({"auto", "mock", "local", "local_qa"})

CREDENTIAL_MISSING_REASON = (
    "Registro de callers configurado e credencial ausente na requisição."
)
CREDENTIAL_UNKNOWN_REASON = (
    "Credencial não registrada no PedroCore; nenhuma identidade pôde ser derivada."
)
REGISTRY_INVALID_REASON = (
    "Registro de callers inválido; nenhuma identidade pode ser derivada com "
    "segurança (fail-closed)."
)
ORIGIN_MISMATCH_REASON = (
    "origin_system declarado é incompatível com a identidade autenticada da "
    "credencial; requisição rejeitada."
)
PROVIDER_SELECTION_REASON = (
    "Consumidor comum não seleciona provider: use provider=auto e deixe a "
    "escolha com o PedroCore."
)
MODEL_SELECTION_REASON = (
    "Consumidor comum não define modelo: seleção de modelo não é canal de "
    "escolha de provider."
)
SHARED_CREDENTIAL_NOTICE = (
    "Identidade derivada de credencial compartilhada: a origem declarada é "
    "aceita como alegação e o isolamento entre projetos depende de credenciais "
    "distintas."
)


def credential_fingerprint(raw_credential: str) -> str:
    """Fingerprint curto e não reversível da credencial.

    Truncado de propósito: serve para correlacionar auditoria, nunca para
    reconstruir, comparar por força bruta ou reutilizar a chave.
    """
    digest = hashlib.sha256((raw_credential or "").encode("utf-8")).hexdigest()
    return f"{FINGERPRINT_PREFIX}_{digest[:FINGERPRINT_CHARS]}"


def current_environment() -> str:
    return (os.environ.get("APP_ENV") or settings.app_env or "development").strip().lower()


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


class CallerIdentityService:
    """Deriva identidade a partir da credencial; nunca do payload."""

    # ------------------------------------------------------------------
    # Registro de callers
    # ------------------------------------------------------------------
    def registry_configured(self) -> bool:
        return bool((os.environ.get(FLAG_CALLER_REGISTRY) or "").strip())

    def _registry_entries(self) -> tuple[list[dict[str, Any]] | None, bool]:
        """Retorna (entradas, inválido). Registro ilegível é fail-closed."""
        raw = (os.environ.get(FLAG_CALLER_REGISTRY) or "").strip()
        if not raw:
            return None, False
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return None, True
        if not isinstance(data, list) or not data:
            return None, True
        entries: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                return None, True
            if not str(item.get("api_key") or "").strip():
                return None, True
            if not str(item.get("project_id") or "").strip():
                return None, True
            entries.append(item)
        return entries, False

    def _context_from_entry(self, entry: dict[str, Any]) -> AuthenticatedCallerContext:
        raw_key = str(entry.get("api_key") or "")
        project_id = _normalize(str(entry.get("project_id")))
        credential_id = str(
            entry.get("credential_id") or credential_fingerprint(raw_key)
        ).strip()

        role_raw = _normalize(str(entry.get("role") or ""))
        try:
            # Least privilege: papel desconhecido vira consumidor comum.
            role = CallerRole(role_raw)
        except ValueError:
            role = CallerRole.COMMON_CONSUMER

        origins = entry.get("allowed_origins")
        if isinstance(origins, list) and origins:
            allowed_origins = tuple(_normalize(str(item)) for item in origins)
        else:
            # Default fail-closed: a credencial só pode alegar a própria origem.
            allowed_origins = (project_id,)

        return AuthenticatedCallerContext(
            credential_id=credential_id,
            caller_role=role,
            environment=_normalize(str(entry.get("environment") or ""))
            or current_environment(),
            authenticated=True,
            project_id=project_id,
            allowed_origins=allowed_origins,
            shared_credential=False,
        )

    # ------------------------------------------------------------------
    # Resolução
    # ------------------------------------------------------------------
    def resolve(self, provided_credential: str | None) -> CallerResolution:
        entries, invalid = self._registry_entries()

        if invalid:
            return CallerResolution(
                error_code=codes.CALLER_REGISTRY_INVALID,
                reason=REGISTRY_INVALID_REASON,
            )

        if entries is not None:
            provided = (provided_credential or "").strip()
            if not provided:
                return CallerResolution(
                    error_code=codes.CALLER_CREDENTIAL_MISSING,
                    reason=CREDENTIAL_MISSING_REASON,
                )
            for entry in entries:
                if hmac.compare_digest(str(entry.get("api_key") or ""), provided):
                    return CallerResolution(context=self._context_from_entry(entry))
            return CallerResolution(
                error_code=codes.CALLER_CREDENTIAL_UNKNOWN,
                reason=CREDENTIAL_UNKNOWN_REASON,
            )

        internal_key = (os.environ.get(FLAG_INTERNAL_API_KEY) or "").strip()
        if internal_key:
            return CallerResolution(context=self._shared_context(internal_key))

        return CallerResolution(context=self.default_context())

    def _shared_context(self, internal_key: str) -> AuthenticatedCallerContext:
        """Única API key global: identidade real, porém não isolada por projeto."""
        credential_id = (
            os.environ.get(FLAG_INTERNAL_CREDENTIAL_ID) or ""
        ).strip() or f"{SHARED_CREDENTIAL_ID}-{credential_fingerprint(internal_key)}"
        return AuthenticatedCallerContext(
            credential_id=credential_id,
            caller_role=CallerRole.TECHNICAL_TOOL,
            environment=current_environment(),
            authenticated=True,
            project_id=None,
            allowed_origins=None,
            shared_credential=True,
        )

    def default_context(self) -> AuthenticatedCallerContext:
        """Contexto usado quando não há credencial apresentada.

        Sem autenticação interna configurada, o PedroCore está em modo
        dev/local e o caller é a ferramenta técnica local (comportamento
        preexistente). Com registro de callers configurado, o default é
        fail-closed: consumidor comum não autenticado.
        """
        if self.registry_configured():
            return AuthenticatedCallerContext(
                credential_id=LOCAL_CREDENTIAL_ID,
                caller_role=CallerRole.COMMON_CONSUMER,
                environment=current_environment(),
                authenticated=False,
                project_id=None,
                allowed_origins=None,
                shared_credential=True,
            )
        return AuthenticatedCallerContext(
            credential_id=LOCAL_CREDENTIAL_ID,
            caller_role=CallerRole.TECHNICAL_TOOL,
            environment=current_environment(),
            authenticated=False,
            project_id=None,
            allowed_origins=None,
            shared_credential=True,
        )

    # ------------------------------------------------------------------
    # Validação da alegação de origem
    # ------------------------------------------------------------------
    def validate_origin_claim(
        self,
        context: AuthenticatedCallerContext,
        declared_origin: str | None,
        derived_project_id: str,
    ) -> OriginClaimResult:
        declared = _normalize(declared_origin)

        if context.allowed_origins is not None and declared not in context.allowed_origins:
            return OriginClaimResult(
                validation=OriginValidation.MISMATCH,
                project_id=context.project_id or derived_project_id,
                declared_origin=declared,
                reason=ORIGIN_MISMATCH_REASON,
            )

        # Credencial vinculada a projeto é soberana: o projeto vem dela, e a
        # origem declarada nunca o substitui.
        if context.allowed_origins is None:
            return OriginClaimResult(
                validation=OriginValidation.NOT_ENFORCED,
                project_id=context.project_id or derived_project_id,
                declared_origin=declared,
                reason=SHARED_CREDENTIAL_NOTICE,
            )

        return OriginClaimResult(
            validation=OriginValidation.MATCH,
            project_id=context.project_id or derived_project_id,
            declared_origin=declared,
        )

    # ------------------------------------------------------------------
    # Restrições por papel
    # ------------------------------------------------------------------
    def evaluate_request_restrictions(
        self,
        context: AuthenticatedCallerContext,
        requested_provider: str,
        requested_model: str | None,
    ) -> CallerRestrictionResult:
        if context.caller_role is not CallerRole.COMMON_CONSUMER:
            return CallerRestrictionResult()

        if _normalize(requested_provider) not in COMMON_CONSUMER_ALLOWED_SELECTIONS:
            return CallerRestrictionResult(
                blocked=True,
                error_code=codes.CALLER_PROVIDER_SELECTION_NOT_ALLOWED,
                reason=PROVIDER_SELECTION_REASON,
            )

        if (requested_model or "").strip():
            return CallerRestrictionResult(
                blocked=True,
                error_code=codes.CALLER_MODEL_SELECTION_NOT_ALLOWED,
                reason=MODEL_SELECTION_REASON,
            )

        return CallerRestrictionResult()


caller_identity_service = CallerIdentityService()
