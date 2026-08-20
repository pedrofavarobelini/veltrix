from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

TRAINING_CANDIDATE_SCHEMA_VERSION = "1.0"
DATASET_FOUNDATION_POLICY_VERSION = "dataset-foundation-v1"
Signature = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
ShortText = Annotated[str, Field(min_length=1, max_length=128)]


class TrainingSourceType(str, Enum):
    INTERACTION_OUTCOME = "interaction_outcome"
    OPERATIONAL_PATTERN = "operational_pattern"
    REPORT_INTELLIGENCE_V2 = "report_intelligence_v2"
    QA_EVIDENCE = "qa_evidence"
    RISK_ANALYSIS = "risk_analysis"
    EXECUTION_OUTCOME = "execution_outcome"
    HUMAN_FEEDBACK = "human_feedback"


class SourceOutcome(str, Enum):
    SUCCESSFUL = "successful"
    FAILED = "failed"
    BLOCKED = "blocked"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class ContentClassification(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataUseAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorized: bool
    allows_neural_training: bool
    basis: Literal["explicit_human", "project_policy", "evaluation_only"]
    authorized_by: ShortText
    authorized_at: datetime
    content_classification: ContentClassification
    confidential_content_approved: bool = False

    @model_validator(mode="after")
    def _timezone_required(self) -> DataUseAuthorization:
        if self.authorized_at.tzinfo is None:
            raise ValueError("authorized_at deve incluir timezone")
        return self


class TrainingEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: TrainingSourceType
    source_id: ShortText
    project_id: ShortText
    source_schema_version: ShortText
    policy_version: ShortText
    outcome: SourceOutcome
    content_signature: Signature
    observed_at: datetime
    run_id: str | None = Field(default=None, max_length=128)
    conversation_id: str | None = Field(default=None, max_length=128)
    verified: bool = False

    @model_validator(mode="after")
    def _timezone_required(self) -> TrainingEvidenceReference:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at deve incluir timezone")
        return self


class CandidateQualitySignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provenance_quality: float = Field(..., ge=0.0, le=1.0)
    evidence_strength: float = Field(..., ge=0.0, le=1.0)
    completeness: float = Field(..., ge=0.0, le=1.0)
    outcome_consistent: bool
    contradiction_detected: bool = False
    qa_result: Literal["passed", "failed", "blocked", "not_available"] = "not_available"


class HumanFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_id: ShortText
    rating: Literal["positive", "negative", "neutral"]
    accepted: bool | None = None
    preferred_alternative_id: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=1000)
    explicitly_provided: bool = False


class TrainingRiskMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_policy_version: ShortText
    predicted_outcome: ShortText
    actual_outcome: ShortText
    gate: str | None = Field(default=None, max_length=64)
    reason_codes: list[ShortText] = Field(default_factory=list, max_length=50)


class TrainingExampleCandidateDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = TRAINING_CANDIDATE_SCHEMA_VERSION
    producer: str = Field(..., min_length=3, max_length=64)
    source_type: TrainingSourceType
    project_id: str = Field(..., min_length=1, max_length=128)
    task_type: str = Field(..., min_length=1, max_length=128)
    input_features: dict[str, JsonValue] = Field(..., min_length=1, max_length=50)
    context_features: dict[str, JsonValue] = Field(default_factory=dict, max_length=50)
    target: dict[str, JsonValue] = Field(..., min_length=1, max_length=50)
    evidence_refs: list[TrainingEvidenceReference] = Field(..., min_length=1, max_length=20)
    quality_signals: CandidateQualitySignals
    feedback: HumanFeedback | None = None
    risk_metadata: TrainingRiskMetadata | None = None
    data_use: DataUseAuthorization
    derived_content_only: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _chronology_and_project(self) -> TrainingExampleCandidateDraft:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at deve incluir timezone")
        normalized_project = self.project_id.strip().lower()
        if any(item.project_id.strip().lower() != normalized_project for item in self.evidence_refs):
            raise ValueError("todas as evidências devem pertencer ao mesmo projeto")
        return self


class TrainingExampleCandidate(TrainingExampleCandidateDraft):
    candidate_id: str = Field(..., pattern=r"^training-candidate-[0-9a-f]{24}$")
    foundation_policy_version: Literal["dataset-foundation-v1"] = (
        DATASET_FOUNDATION_POLICY_VERSION
    )


class PrivacyFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    category: str
    field_path: str


class CandidateEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["eligible", "rejected"]
    policy_version: Literal["dataset-foundation-v1"] = DATASET_FOUNDATION_POLICY_VERSION
    candidate: TrainingExampleCandidate | None = None
    rejection_codes: list[str] = Field(default_factory=list)
    privacy_findings: list[PrivacyFinding] = Field(default_factory=list)
    persisted: Literal[False] = False
    training_started: Literal[False] = False
    automatic_collection_performed: Literal[False] = False


class TrainingSourceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: TrainingSourceType
    entity: str
    module: str
    required_provenance: list[str]
    target_basis: str
    automatic_collection: Literal[False] = False
