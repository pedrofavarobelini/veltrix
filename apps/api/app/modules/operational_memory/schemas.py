from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.contracts.codes import WarningItem

OPERATIONAL_MEMORY_SCHEMA_VERSION = "1.0"

ShortText = Annotated[str, Field(min_length=1, max_length=128)]


class PatternType(str, Enum):
    SUCCESS_PATTERN = "SUCCESS_PATTERN"
    FAILURE_PATTERN = "FAILURE_PATTERN"
    ANTI_PATTERN = "ANTI_PATTERN"
    USER_PREFERENCE = "USER_PREFERENCE"
    PROJECT_PATTERN = "PROJECT_PATTERN"
    PROVIDER_PATTERN = "PROVIDER_PATTERN"
    PROMPT_PATTERN = "PROMPT_PATTERN"
    RISK_PATTERN = "RISK_PATTERN"


class MemoryLifecycle(str, Enum):
    DETECTED = "DETECTED"
    ACTIVE = "ACTIVE"
    MITIGATED = "MITIGATED"
    RESOLVED = "RESOLVED"


class EvidenceSourceType(str, Enum):
    REPORT = "report"
    INTERACTION_OUTCOME = "interaction_outcome"
    HUMAN_VALIDATION = "human_validation"


class EvidenceEffect(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    MITIGATES = "mitigates"
    RESOLVES = "resolves"


class CandidateDecision(str, Enum):
    DETECTED = "detected"
    PROMOTED = "promoted"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"


class EvidenceReferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: EvidenceSourceType
    source_id: str = Field(..., min_length=1, max_length=128)
    effect: EvidenceEffect = EvidenceEffect.SUPPORTS


class EvidenceReference(EvidenceReferenceInput):
    source_reliability: float = Field(..., ge=0.0, le=1.0)
    evidence_strength: float = Field(..., ge=0.0, le=1.0)
    context_match: float = Field(..., ge=0.0, le=1.0)
    qa_validated: bool = False
    human_validated: bool = False
    observed_at: datetime


class OperationalPattern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern_id: str
    pattern_type: PatternType
    pattern_key: str
    task_type: str
    summary: str


class ConfidenceBreakdown(BaseModel):
    source_reliability: float = Field(..., ge=0.0, le=1.0)
    evidence_strength: float = Field(..., ge=0.0, le=1.0)
    frequency: float = Field(..., ge=0.0, le=1.0)
    recency: float = Field(..., ge=0.0, le=1.0)
    context_match: float = Field(..., ge=0.0, le=1.0)
    qa_validation: float = Field(..., ge=0.0, le=1.0)
    human_validation: float = Field(..., ge=0.0, le=1.0)
    contradiction_penalty: float = Field(..., ge=0.0, le=1.0)


class LifecycleTransition(BaseModel):
    from_lifecycle: MemoryLifecycle | None = None
    to_lifecycle: MemoryLifecycle
    reason: str
    at: datetime


class LearningCandidateBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = OPERATIONAL_MEMORY_SCHEMA_VERSION
    candidate_id: str = Field(..., min_length=3, max_length=128)
    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    pattern_type: PatternType
    pattern_key: str = Field(..., min_length=3, max_length=128, pattern=r"^[a-z0-9_.:-]+$")
    task_type: str = Field(..., min_length=1, max_length=128)
    summary: str = Field(..., min_length=1, max_length=500)


class LearningCandidateInput(LearningCandidateBase):
    evidence: list[EvidenceReferenceInput] = Field(..., min_length=1, max_length=20)


class LearningCandidate(LearningCandidateBase):
    pattern_id: str
    evidence: list[EvidenceReference]
    confidence: float = Field(..., ge=0.0, le=1.0)
    decision: CandidateDecision
    policy_version: str
    caller_role: str
    environment: str
    created_at: datetime
    stored_at: datetime
    retention_until: datetime


class OperationalMemoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    project_id: str
    pattern: OperationalPattern
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_breakdown: ConfidenceBreakdown
    lifecycle: MemoryLifecycle
    candidate_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    contradictions: list[EvidenceReference] = Field(default_factory=list)
    sample_size: int = Field(default=0, ge=0)
    policy_version: str
    lifecycle_history: list[LifecycleTransition] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    retention_until: datetime


class LearningCandidateResponse(BaseModel):
    status: str = "ok"
    stored: bool = False
    duplicate: bool = False
    candidate: LearningCandidate | None = None
    memory: OperationalMemoryEntry | None = None
    warnings: list[WarningItem] = Field(default_factory=list)


class OperationalMemoryPageResponse(BaseModel):
    status: str = "ok"
    project_id: str
    items: list[OperationalMemoryEntry] = Field(default_factory=list)
    total: int = 0
    limit: int
    offset: int
    warnings: list[WarningItem] = Field(default_factory=list)


class OperationalMemoryDeleteResponse(BaseModel):
    status: str = "ok"
    project_id: str
    deleted_candidates: int = 0
    deleted_memories: int = 0
    warnings: list[WarningItem] = Field(default_factory=list)
