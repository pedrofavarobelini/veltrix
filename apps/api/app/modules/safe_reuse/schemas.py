from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SAFE_REUSE_SCHEMA_VERSION = "1.0"
SAFE_REUSE_POLICY_VERSION = "safe-reuse-v1"
Signature = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]


class ReuseMode(str, Enum):
    DIRECT_REUSE = "DIRECT_REUSE"
    TEMPLATE_REUSE = "TEMPLATE_REUSE"
    KNOWLEDGE_REUSE = "KNOWLEDGE_REUSE"
    ANTI_PATTERN = "ANTI_PATTERN"
    NO_REUSE = "NO_REUSE"


class ValidationStatus(str, Enum):
    VALIDATED = "VALIDATED"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"
    FAILED = "FAILED"


class ReuseFingerprint(BaseModel):
    """Signatures describe equivalence without transporting the underlying data."""

    model_config = ConfigDict(extra="forbid")

    input_signature: Signature
    context_signature: Signature
    data_signature: Signature
    project_id: str = Field(..., min_length=1, max_length=128)
    user_scope_signature: Signature | None = None
    family_scope_signature: Signature | None = None
    permissions: list[str] = Field(default_factory=list, max_length=32)
    environment: str = Field(..., min_length=1, max_length=32)
    temporal_state_signature: Signature
    policy_version: str = Field(..., min_length=1, max_length=64)
    dependency_version: str = Field(..., min_length=1, max_length=64)


class ReuseCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., min_length=3, max_length=128)
    proposed_mode: ReuseMode
    source_fingerprint: ReuseFingerprint | None = None
    validation_status: ValidationStatus = ValidationStatus.UNKNOWN
    validation_signature: Signature | None = None
    validated_at: datetime | None = None
    valid_until: datetime | None = None
    template_id: str | None = Field(default=None, min_length=1, max_length=128)
    template_version: str | None = Field(default=None, min_length=1, max_length=64)
    memory_id: str | None = Field(default=None, min_length=1, max_length=128)


class ReuseEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = SAFE_REUSE_SCHEMA_VERSION
    evaluation_id: str | None = Field(default=None, min_length=3, max_length=128)
    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    current_fingerprint: ReuseFingerprint
    candidate: ReuseCandidate


class ReuseDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = SAFE_REUSE_SCHEMA_VERSION
    evaluation_id: str
    project_id: str
    candidate_id: str
    mode: ReuseMode
    provider_bypass: Literal[False] = False
    reusable_response_returned: Literal[False] = False
    matched_memory_id: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    invalidated_dimensions: list[str] = Field(default_factory=list)
    policy_version: Literal["safe-reuse-v1"] = SAFE_REUSE_POLICY_VERSION
    evaluated_at: datetime
