from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

TRAINING_CANDIDATE_SCHEMA_VERSION = "1.0"
DATASET_FOUNDATION_POLICY_VERSION = "dataset-foundation-v1"
TRAINING_ACQUISITION_POLICY_VERSION = "training-acquisition-v1"
DATASET_READINESS_POLICY_VERSION = "dataset-readiness-v2"
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
    # Stage 13 da Elyra: agregado numerico sanitizado de report_snapshot.
    ELYRA_REPORT_SNAPSHOT = "elyra_report_snapshot"


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


class TrainingPurpose(str, Enum):
    GENERATIVE_SFT = "generative_sft"
    PREFERENCE = "preference"
    RISK = "risk"
    EVALUATION_ONLY = "evaluation_only"


class EligibilityDecision(str, Enum):
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    REQUIRES_REVIEW = "requires_review"


class PrivacyClassification(str, Enum):
    SAFE = "safe"
    REQUIRES_SANITIZATION = "requires_sanitization"
    REJECTED_SENSITIVE = "rejected_sensitive"


class CandidateLifecycle(str, Enum):
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    REVIEW_REQUIRED = "review_required"
    EXCLUDED = "excluded"
    REVOKED = "revoked"
    CONSUMED = "consumed"


class DataUseAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorized: bool
    allows_neural_training: bool
    basis: Literal["explicit_human", "project_policy", "evaluation_only"]
    authorized_by: ShortText
    authorized_at: datetime
    authorized_project: ShortText
    authorized_scope: ShortText
    training_purpose: TrainingPurpose
    policy_version: Literal["training-acquisition-v1"] = TRAINING_ACQUISITION_POLICY_VERSION
    authorization_source: ShortText
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
    source_reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    outcome_known: bool = False
    qa_validated: bool = False
    human_feedback_present: bool = False
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


class TrainingSourceSelection(BaseModel):
    """Seleção explícita de uma evidência operacional já persistida."""

    model_config = ConfigDict(extra="forbid")

    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    source_type: TrainingSourceType
    source_id: ShortText
    training_purpose: TrainingPurpose


class TrainingCandidateProposal(BaseModel):
    """Material estruturado produzido somente pelos adapters internos."""

    model_config = ConfigDict(extra="forbid")

    producer: str = Field(..., min_length=3, max_length=64)
    source_type: TrainingSourceType
    project_id: str = Field(..., min_length=1, max_length=128)
    task_type: str = Field(..., min_length=1, max_length=128)
    training_purpose: TrainingPurpose
    input_features: dict[str, JsonValue] = Field(..., min_length=1, max_length=50)
    context_features: dict[str, JsonValue] = Field(default_factory=dict, max_length=50)
    target: dict[str, JsonValue] = Field(..., min_length=1, max_length=50)
    evidence_refs: list[TrainingEvidenceReference] = Field(..., min_length=1, max_length=20)
    quality_signals: CandidateQualitySignals
    feedback: HumanFeedback | None = None
    risk_metadata: TrainingRiskMetadata | None = None
    derived_content_only: Literal[True] = True
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _chronology_and_project(self) -> TrainingCandidateProposal:
        if self.proposed_at.tzinfo is None:
            raise ValueError("proposed_at deve incluir timezone")
        normalized_project = self.project_id.strip().lower()
        if any(item.project_id.strip().lower() != normalized_project for item in self.evidence_refs):
            raise ValueError("todas as evidências devem pertencer ao mesmo projeto")
        return self


class TrainingAuthorizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: ShortText
    authorized_scope: ShortText
    authorization_source: ShortText
    basis: Literal["explicit_human", "project_policy", "evaluation_only"]
    content_classification: ContentClassification
    confidential_content_approved: bool = False


class TrainingCandidateReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: ShortText
    decision: Literal["approve", "exclude"]
    reason_code: ShortText


class TrainingCandidateStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: ShortText
    reason_code: ShortText


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


class EligibilityEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: EligibilityDecision
    policy_version: Literal["training-acquisition-v1"] = TRAINING_ACQUISITION_POLICY_VERSION
    privacy_classification: PrivacyClassification
    reason_codes: list[str] = Field(default_factory=list)
    privacy_findings: list[PrivacyFinding] = Field(default_factory=list)


class TrainingCandidateRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., pattern=r"^training-candidate-[0-9a-f]{24}$")
    project_id: ShortText
    source_type: TrainingSourceType
    source_id: ShortText | None = None
    source_reference_hash: Signature
    fingerprint: Signature
    task_type: ShortText
    training_purpose: TrainingPurpose
    lifecycle: CandidateLifecycle
    eligibility: EligibilityDecision
    privacy_classification: PrivacyClassification
    policy_version: Literal["training-acquisition-v1"] = TRAINING_ACQUISITION_POLICY_VERSION
    reason_codes: list[str] = Field(default_factory=list)
    privacy_findings: list[PrivacyFinding] = Field(default_factory=list)
    proposal: TrainingCandidateProposal | None = None
    candidate: TrainingExampleCandidate | None = None
    authorization: DataUseAuthorization | None = None
    review_approved: bool = False
    reviewed_by: ShortText | None = None
    reviewed_at: datetime | None = None
    excluded_reason: ShortText | None = None
    revoked_reason: ShortText | None = None
    revoked_by: ShortText | None = None
    revoked_at: datetime | None = None
    consumed_dataset_ids: list[ShortText] = Field(default_factory=list, max_length=100)
    created_at: datetime
    updated_at: datetime


class TrainingCandidateMutationResponse(BaseModel):
    status: Literal["ok"] = "ok"
    stored: bool = False
    duplicate: bool = False
    record: TrainingCandidateRecord


class TrainingCandidatePageResponse(BaseModel):
    status: Literal["ok"] = "ok"
    project_id: ShortText
    items: list[TrainingCandidateRecord] = Field(default_factory=list)
    total: int = 0
    limit: int
    offset: int


class FingerprintDistribution(BaseModel):
    unique_fingerprints: int = 0
    duplicate_groups: int = 0
    max_frequency: int = 0
    duplicate_ratio: float = 0.0


class DatasetReadinessMetrics(BaseModel):
    total_candidates: int = 0
    authorized_candidates: int = 0
    eligible_candidates: int = 0
    review_required: int = 0
    excluded: int = 0
    revoked: int = 0
    by_source: dict[str, int] = Field(default_factory=dict)
    by_project: dict[str, int] = Field(default_factory=dict)
    by_task_type: dict[str, int] = Field(default_factory=dict)
    by_training_purpose: dict[str, int] = Field(default_factory=dict)
    with_known_outcome: int = 0
    with_qa_evidence: int = 0
    with_human_feedback: int = 0
    with_verified_provenance: int = 0
    contradictions: int = 0
    privacy_rejections: int = 0
    fingerprint_distribution: FingerprintDistribution = Field(
        default_factory=FingerprintDistribution
    )


class DatasetReadinessPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_version: Literal["dataset-readiness-v2"] = DATASET_READINESS_POLICY_VERSION
    minimum_authorized_candidates: int | None = Field(default=None, ge=1)
    minimum_source_types: int = Field(default=3, ge=1)
    minimum_task_types: int = Field(default=3, ge=1)
    minimum_training_purposes: int = Field(default=2, ge=1)
    minimum_known_outcome_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
    minimum_qa_coverage_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    minimum_verified_provenance_ratio: float = Field(default=1.0, ge=0.0, le=1.0)
    maximum_duplicate_ratio: float = Field(default=0.1, ge=0.0, le=1.0)
    maximum_contradiction_ratio: float = Field(default=0.1, ge=0.0, le=1.0)


class DatasetReadinessReport(BaseModel):
    status: Literal["ok"] = "ok"
    project_id: ShortText
    readiness: Literal["DATASET_READY", "DATASET_NOT_READY"]
    policy: DatasetReadinessPolicy
    metrics: DatasetReadinessMetrics
    blocker_codes: list[str] = Field(default_factory=list)
    canonical_dataset_created: Literal[False] = False
    training_started: Literal[False] = False


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
