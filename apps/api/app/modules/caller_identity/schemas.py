"""Identidade autenticada do caller (MULTI-PROVIDER-SAFE-EVOLUTION, Etapa 2).

A identidade do consumidor passa a ser derivada da CREDENCIAL autenticada, não
do payload. `origin_system` continua aceito por compatibilidade, mas como
alegação validada contra a identidade — nunca como fonte soberana.

Nenhum valor de credencial é armazenado aqui: apenas um `credential_id` não
secreto (ID configurado ou fingerprint truncado), estável para auditoria e
incapaz de reconstruir a chave.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator

# Identificador de credencial: não secreto, curto e estável.
_CREDENTIAL_ID = re.compile(r"^[A-Za-z0-9_.:-]{3,64}$")


class CallerRole(str, Enum):
    """Papéis mínimos. Nenhum papel administrativo é criado nesta etapa."""

    COMMON_CONSUMER = "common_consumer"
    TECHNICAL_TOOL = "technical_tool"


class OriginValidation(str, Enum):
    MATCH = "match"
    # Credencial compartilhada não distingue projeto: a origem declarada é
    # aceita como alegação, e isso fica explícito na auditoria.
    NOT_ENFORCED = "not_enforced"
    MISMATCH = "mismatch"


class AuthenticatedCallerContext(BaseModel):
    """Contexto autenticado do caller, derivado da credencial."""

    model_config = ConfigDict(frozen=True)

    credential_id: str
    caller_role: CallerRole
    environment: str
    authenticated: bool = False
    # None => projeto derivado da origem validada (credencial compartilhada).
    project_id: str | None = None
    # None => a credencial não restringe origem (compartilhada/legada).
    allowed_origins: tuple[str, ...] | None = None
    shared_credential: bool = True

    @model_validator(mode="after")
    def _check(self) -> AuthenticatedCallerContext:
        if not _CREDENTIAL_ID.match(self.credential_id):
            raise ValueError(
                "credential_id deve ser um identificador curto e não secreto: "
                f"{self.credential_id!r}"
            )
        if self.project_id is not None and not self.project_id.strip():
            raise ValueError("project_id vazio não é identidade válida.")
        if self.allowed_origins is not None and not self.allowed_origins:
            raise ValueError(
                "allowed_origins vazio bloquearia toda origem; use None para "
                "credencial sem restrição de origem."
            )
        return self

    @property
    def identity_is_project_bound(self) -> bool:
        """True quando a credencial, sozinha, determina o projeto."""
        return self.project_id is not None and not self.shared_credential


class CallerResolution(BaseModel):
    """Resultado da resolução de credencial. Fail-closed por construção."""

    model_config = ConfigDict(frozen=True)

    context: AuthenticatedCallerContext | None = None
    error_code: str | None = None
    reason: str | None = None

    @property
    def rejected(self) -> bool:
        return self.context is None


class OriginClaimResult(BaseModel):
    """Validação da alegação `origin_system` contra a identidade autenticada."""

    model_config = ConfigDict(frozen=True)

    validation: OriginValidation
    project_id: str
    declared_origin: str
    reason: str | None = None

    @property
    def rejected(self) -> bool:
        return self.validation is OriginValidation.MISMATCH


class CallerRestrictionResult(BaseModel):
    """Restrições de requisição aplicadas ao papel do caller."""

    model_config = ConfigDict(frozen=True)

    blocked: bool = False
    error_code: str | None = None
    reason: str | None = None
