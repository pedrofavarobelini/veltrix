"""Política determinística de roteamento (Etapas 4 e 5).

Calcula, de forma determinística, qual provider/modelo SERIA escolhido por uma
política multi-provider. O mesmo resultado é usado como observação em
``shadow`` e como escolha real em ``enforced``; o avaliador nunca chama
provider algum.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

POLICY_VERSION = "static-priority-v2"


class RoutingMode(str, Enum):
    """Modo interno; nunca é controlado pelo payload do consumidor."""

    LEGACY = "legacy"
    SHADOW = "shadow"
    ENFORCED = "enforced"


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
    CIRCUIT_OPEN = "circuit_open"
    HALF_OPEN_BUSY = "half_open_busy"
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
    """Decisão única da política, compatível com a projeção shadow existente."""

    model_config = ConfigDict(frozen=True, protected_namespaces=())

    enabled: bool = False
    routing_mode: RoutingMode = RoutingMode.LEGACY
    configuration_valid: bool = True
    configuration_reason: str | None = None
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
