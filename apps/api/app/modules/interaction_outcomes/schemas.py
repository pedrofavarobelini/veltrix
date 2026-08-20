from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.contracts.codes import WarningItem

INTERACTION_OUTCOME_SCHEMA_VERSION = "1.0"
Signature = Annotated[
    str,
    Field(pattern=r"^sha256:[0-9a-f]{64}$"),
]
ShortText = Annotated[str, Field(min_length=1, max_length=128)]


class ResponseCharacteristics(BaseModel):
    """Características observáveis; nunca contém prompt ou resposta bruta."""

    model_config = ConfigDict(extra="forbid")

    length_bucket: Literal["empty", "short", "medium", "long"] = "medium"
    structured: bool = False
    contains_citations: bool = False
    safety_disclaimer: bool = False
    truncated: bool = False


class InteractionOutcomeInput(BaseModel):
    """Outcome declarado por uma ferramenta técnica autenticada."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = INTERACTION_OUTCOME_SCHEMA_VERSION
    outcome_id: str = Field(..., min_length=3, max_length=128)
    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    conversation_id: str = Field(..., min_length=1, max_length=128)
    message_id: str = Field(..., min_length=1, max_length=128)
    task_type: str = Field(..., min_length=1, max_length=128)
    input_signature: Signature
    context_signature: Signature
    provider: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=128)
    response_strategy: str = Field(..., min_length=1, max_length=128)
    response_characteristics: ResponseCharacteristics = Field(
        default_factory=ResponseCharacteristics
    )
    fallback_used: bool = False
    regeneration_used: bool = False
    feedback: Literal["positive", "negative", "neutral", "unknown"] = "unknown"
    accepted: bool | None = None
    rejected: bool | None = None
    quality_signals: list[ShortText] = Field(default_factory=list, max_length=50)
    audit_id: str | None = Field(default=None, max_length=128)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_outcome(self) -> InteractionOutcomeInput:
        if self.accepted is True and self.rejected is True:
            raise ValueError("accepted e rejected não podem ser true simultaneamente")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at deve incluir timezone")
        return self


class InteractionOutcome(InteractionOutcomeInput):
    """Representação persistida com provenance e lifecycle autoritativos."""

    caller_role: str
    environment: str
    lifecycle: Literal["active"] = "active"
    stored_at: datetime
    retention_until: datetime


class InteractionOutcomeIngestResponse(BaseModel):
    status: str = "ok"
    stored: bool = False
    duplicate: bool = False
    outcome: InteractionOutcome | None = None
    warnings: list[WarningItem] = Field(default_factory=list)


class InteractionOutcomePageResponse(BaseModel):
    status: str = "ok"
    project_id: str
    items: list[InteractionOutcome] = Field(default_factory=list)
    total: int = 0
    limit: int
    offset: int
    warnings: list[WarningItem] = Field(default_factory=list)


class InteractionOutcomeDeleteResponse(BaseModel):
    status: str = "ok"
    project_id: str
    deleted: int = 0
    warnings: list[WarningItem] = Field(default_factory=list)
