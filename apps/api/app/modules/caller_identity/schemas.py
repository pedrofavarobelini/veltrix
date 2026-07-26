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

# Projeto atribuído a quem não prova projeto algum. Não é um projeto real e
# nunca aparece na matriz de autorização de provider real.
SHARED_OR_UNKNOWN_PROJECT_ID = "shared_or_unknown"


class CallerRole(str, Enum):
    """Papéis mínimos. Nenhum papel administrativo é criado nesta etapa."""

    COMMON_CONSUMER = "common_consumer"
    TECHNICAL_TOOL = "technical_tool"


class IdentityStrength(str, Enum):
    """Quão inequívoca é a identidade de projeto do caller.

    Autenticado != identificado de forma inequívoca != autorizado para
    provider real. Somente `REGISTERED` prova projeto por credencial.
    """

    # Credencial registrada e vinculada a um projeto, papel e origens.
    REGISTERED = "registered"
    # Sem autenticação interna configurada: deploy dev/local, operador local.
    # A origem declarada é aceita, porém nada a comprova.
    LOCAL_TRUSTED = "local_trusted"
    # Credencial compartilhada/global ou ausente com registro ativo: não
    # identifica projeto e opera sempre com menor privilégio.
    AMBIGUOUS = "ambiguous"


class OriginValidation(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    # Identidade ambígua: a alegação é registrada em auditoria e NUNCA vira
    # identidade de projeto.
    NOT_TRUSTED = "not_trusted"
    # Modo dev/local sem credencial: alegação aceita para policy, sem prova.
    LOCAL_UNVERIFIED = "local_unverified"


class AuthenticatedCallerContext(BaseModel):
    """Contexto autenticado do caller, derivado da credencial."""

    model_config = ConfigDict(frozen=True)

    credential_id: str
    caller_role: CallerRole
    environment: str
    identity_strength: IdentityStrength
    authenticated: bool = False
    # None => projeto derivado da origem declarada (apenas para identidades
    # que podem derivá-lo). Identidade ambígua recebe SHARED_OR_UNKNOWN.
    project_id: str | None = None
    # None => a credencial não restringe origem.
    allowed_origins: tuple[str, ...] | None = None

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

        if self.identity_strength is IdentityStrength.AMBIGUOUS:
            if self.caller_role is not CallerRole.COMMON_CONSUMER:
                raise ValueError(
                    "identidade ambígua opera com menor privilégio e nunca "
                    "recebe papel de ferramenta técnica."
                )
            if self.project_id != SHARED_OR_UNKNOWN_PROJECT_ID:
                raise ValueError(
                    "identidade ambígua não pode assumir projeto: use "
                    f"{SHARED_OR_UNKNOWN_PROJECT_ID!r}."
                )

        if self.identity_strength is IdentityStrength.REGISTERED:
            if not self.project_id or self.project_id == SHARED_OR_UNKNOWN_PROJECT_ID:
                raise ValueError(
                    "credencial registrada precisa declarar project_id real."
                )
            if self.allowed_origins is None:
                raise ValueError(
                    "credencial registrada precisa declarar origens permitidas."
                )

        if self.identity_strength is IdentityStrength.LOCAL_TRUSTED:
            if self.project_id is not None:
                raise ValueError(
                    "contexto local/dev deriva o projeto da origem declarada; "
                    "não pode fixar project_id."
                )

        return self

    @property
    def shared_credential(self) -> bool:
        """True quando a credencial não vincula o caller a um projeto."""
        return self.identity_strength is not IdentityStrength.REGISTERED

    @property
    def identity_is_project_bound(self) -> bool:
        """True quando a credencial, sozinha, determina o projeto."""
        return self.identity_strength is IdentityStrength.REGISTERED

    @property
    def establishes_project_identity(self) -> bool:
        """False para identidade ambígua: ela nunca assume projeto algum."""
        return self.identity_strength is not IdentityStrength.AMBIGUOUS


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
    """Validação da alegação `origin_system` contra a identidade autenticada.

    Separa deliberadamente dois conceitos que a Etapa 2 havia fundido:

    - `identity_project_id`: projeto **provado** pela identidade. É o único
      valor que alimenta a matriz de autorização de provider real.
    - `context_project_id`: projeto usado para policy/tasks (Project Context),
      preservando o comportamento público existente.
    """

    model_config = ConfigDict(frozen=True)

    validation: OriginValidation
    identity_project_id: str
    context_project_id: str
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
