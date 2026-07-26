"""Política de roteamento em shadow mode (Etapa 4).

Calcula, de forma determinística, qual provider/modelo SERIA escolhido por uma
política multi-provider futura — sem nunca alterar a execução real, sem chamar
provider algum e sem consultar uma segunda IA.

A decisão é observação, não roteamento: o pipeline continua usando
`AUTO_REAL_PROVIDER_CANDIDATES` (Gemini-only).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

POLICY_VERSION = "shadow-static-priority-v1"


class EliminationReason(str, Enum):
    """Motivo determinístico e sanitizado da eliminação de um candidato."""

    NOT_REGISTERED = "not_registered"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_CONFIGURED = "not_configured"
    NOT_HOMOLOGATED = "not_homologated"
    AMBIGUOUS_IDENTITY = "ambiguous_identity"
    NOT_AUTHORIZED = "not_authorized"
    TASK_INCOMPATIBLE = "task_incompatible"
    MODEL_INCOMPATIBLE = "model_incompatible"
    MODEL_NOT_HOMOLOGATED = "model_not_homologated"
    MODEL_NOT_AUTHORIZED = "model_not_authorized"
    SAFE_MODE_BLOCKED = "safe_mode_blocked"
    PROJECT_POLICY_BLOCKED = "project_policy_blocked"


class ShadowCandidate(BaseModel):
    """Candidato avaliado pela política shadow. Nunca executado."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    provider_id: str
    model_id: str | None = None
    priority: int
    eliminated: bool = False
    elimination_reason: EliminationReason | None = None


class ShadowRoutingDecision(BaseModel):
    """Decisão planejada pela política shadow, sem qualquer efeito real."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    enabled: bool = False
    project_id: str = ""
    task_type: str = ""
    candidates_considered: tuple[ShadowCandidate, ...] = Field(default_factory=tuple)
    candidates_eliminated: tuple[ShadowCandidate, ...] = Field(default_factory=tuple)
    selected_provider: str | None = None
    selected_model: str | None = None
    selection_reason: str = ""
    policy_version: str = POLICY_VERSION
    # Comparação de identificadores apenas: o candidato shadow NUNCA é
    # executado para verificar a diferença.
    would_differ_from_actual: bool | None = None
