from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.qa_response.schemas import QAResponseSkeleton, ReleaseGateResult
from app.modules.report_intelligence.schemas import IntelligenceReportEnvelopeV2
from app.modules.risk_engine.execution_contract_schemas import (
    ExecutionContract,
    HumanReviewRecord,
    RiskGate,
)
from app.modules.risk_engine.schemas import RiskRequest

POST_EXECUTION_POLICY_VERSION = "post-execution-v1"


class DiffEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diff_signature: str = Field(..., pattern=r"^sha256:[a-f0-9]{64}$")
    files_count: int = Field(..., ge=0, le=10000)
    additions: int = Field(..., ge=0)
    deletions: int = Field(..., ge=0)


class CommandEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: str = Field(..., min_length=1, max_length=128)
    command: str = Field(..., min_length=1, max_length=256)
    exit_code: int

    @field_validator("command")
    @classmethod
    def _command_must_not_contain_inline_secret(cls, value: str) -> str:
        forbidden = ("api_key=", "apikey=", "token=", "password=", "secret=")
        if any(marker in value.lower() for marker in forbidden):
            raise ValueError("command evidence não pode transportar secret inline")
        return value


class TestEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite: str = Field(..., min_length=1, max_length=128)
    status: Literal["passed", "failed", "skipped"]
    passed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)


class SecurityEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scanner: str = Field(..., min_length=1, max_length=128)
    status: Literal["passed", "failed", "blocked", "not_run"]
    critical: int = Field(default=0, ge=0)
    high: int = Field(default=0, ge=0)
    medium: int = Field(default=0, ge=0)
    low: int = Field(default=0, ge=0)


class MigrationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    migration_id: str = Field(..., min_length=1, max_length=128)
    status: Literal["passed", "failed", "rolled_back", "not_run"]
    destructive: bool = False
    rollback_performed: bool = False


class ExecutionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(..., min_length=3, max_length=128)
    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    contract: ExecutionContract
    current_request: RiskRequest
    human_review: HumanReviewRecord | None = None
    started_at: datetime
    finished_at: datetime
    files_changed: list[str] = Field(default_factory=list, max_length=500)
    diff: DiffEvidence | None = None
    commands: list[CommandEvidence] = Field(default_factory=list, max_length=100)
    tests: list[TestEvidence] = Field(default_factory=list, max_length=100)
    security_results: list[SecurityEvidence] = Field(default_factory=list, max_length=50)
    migration_results: list[MigrationEvidence] = Field(default_factory=list, max_length=50)
    scope_changes: list[str] = Field(default_factory=list, max_length=500)
    unexpected_effects: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def _chronology_and_scope(self) -> ExecutionEvidence:
        if self.finished_at < self.started_at:
            raise ValueError("finished_at não pode anteceder started_at")
        return self


class ExecutionComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_targets: list[str] = Field(default_factory=list)
    actual_targets: list[str] = Field(default_factory=list)
    unexpected_files: list[str] = Field(default_factory=list)
    scope_deviation: list[str] = Field(default_factory=list)
    forbidden_commands: list[str] = Field(default_factory=list)
    failed_tests: list[str] = Field(default_factory=list)
    security_findings: list[str] = Field(default_factory=list)
    migration_incidents: list[str] = Field(default_factory=list)
    unexpected_effects: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


class PredictedVsActual(BaseModel):
    model_config = ConfigDict(extra="forbid")

    predicted_dimensions: dict[str, float] = Field(default_factory=dict)
    actual_issue_codes: list[str] = Field(default_factory=list)
    predicted_risk_materialized: bool = False
    unpredicted_issue_detected: bool = False


class OperationalMemoryProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str | None = None
    memory_id: str | None = None
    lifecycle: str | None = None
    duplicate: bool = False


class PostExecutionOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome_id: str
    policy_version: Literal["post-execution-v1"] = POST_EXECUTION_POLICY_VERSION
    project_id: str
    evidence_id: str
    contract_id: str
    risk_analysis_id: str
    effective_gate: RiskGate
    status: Literal["passed", "failed", "blocked"]
    contract_valid: bool
    comparison: ExecutionComparison
    predicted_vs_actual: PredictedVsActual
    qa: QAResponseSkeleton
    qa_release_gate: ReleaseGateResult
    execution_outcome_report: IntelligenceReportEnvelopeV2
    report_persisted: bool = False
    report_duplicate: bool = False
    operational_memory: OperationalMemoryProjection
    trace: list[str] = Field(default_factory=list)
    target_operation_executed_by_risk_engine: Literal[False] = False
    provider_called_by_risk_engine: Literal[False] = False
