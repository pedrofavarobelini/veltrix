"""Decisão de autorização de provider (MULTI-PROVIDER-SAFE-EVOLUTION, Etapa 2)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class AuthorizationResult(str, Enum):
    ALLOWED = "allowed"
    DENIED = "denied"
    # Provider não externo (mock/local_qa/local_model): a matriz de provider
    # real não se aplica; as políticas próprias de cada um continuam valendo.
    NOT_APPLICABLE = "not_applicable"


class ProviderAuthorizationDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: AuthorizationResult
    provider_id: str
    project_id: str
    caller_role: str
    environment: str
    error_code: str | None = None
    reason: str = ""

    @property
    def allowed(self) -> bool:
        return self.result is not AuthorizationResult.DENIED

    @property
    def denied(self) -> bool:
        return self.result is AuthorizationResult.DENIED
