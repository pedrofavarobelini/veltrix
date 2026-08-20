from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.contracts.codes import WarningItem
from app.modules.operational_memory.schemas import MemoryLifecycle, PatternType

RETRIEVAL_SCHEMA_VERSION = "1.0"
RETRIEVAL_POLICY_VERSION = "retrieval-v1"


class RetrievalQuery(BaseModel):
    """Structured query only; deliberately not a raw prompt transport."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = RETRIEVAL_SCHEMA_VERSION
    query_id: str | None = Field(default=None, min_length=3, max_length=128)
    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    task_type: str | None = Field(default=None, min_length=1, max_length=128)
    keywords: list[str] = Field(default_factory=list, max_length=12)
    pattern_types: list[PatternType] = Field(default_factory=list, max_length=8)
    lifecycles: list[MemoryLifecycle] = Field(default_factory=list, max_length=4)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    min_evidence_count: int = Field(default=1, ge=0, le=20)
    recency_days: int | None = Field(default=None, ge=1, le=3650)
    include_anti_patterns: bool = False
    max_results: int = Field(default=5, ge=1, le=5)
    max_context_chars: int = Field(default=2000, ge=200, le=2000)


class RetrievedMemory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    pattern_id: str
    pattern_type: PatternType
    lifecycle: MemoryLifecycle
    task_type: str
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_count: int = Field(..., ge=0)
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    policy_version: str
    updated_at: datetime


class RetrievalCandidateTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    selected: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)


class RetrievalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    schema_version: Literal["1.0"] = RETRIEVAL_SCHEMA_VERSION
    query_id: str
    project_id: str
    policy_version: Literal["retrieval-v1"] = RETRIEVAL_POLICY_VERSION
    items: list[RetrievedMemory] = Field(default_factory=list)
    candidates: list[RetrievalCandidateTrace] = Field(default_factory=list)
    context_chars: int = Field(default=0, ge=0)
    warnings: list[WarningItem] = Field(default_factory=list)
