from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.operational_memory.schemas import MemoryLifecycle, PatternType
from app.modules.risk_engine.schemas import RiskRequest

HISTORICAL_RISK_POLICY_VERSION = "historical-risk-v1"
CURRENT_RISK_POLICY_VERSION = "pre-execution-risk-v1"
RiskStrategy = Literal[
    "deterministic_only",
    "semantic_only",
    "history_only",
    "hybrid",
]


class HistoricalRiskQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    window_start: datetime
    window_end: datetime
    task_types: list[str] = Field(default_factory=list, max_length=50)
    pattern_types: list[PatternType] = Field(default_factory=list, max_length=8)
    lifecycles: list[MemoryLifecycle] = Field(default_factory=list, max_length=4)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_policy_versions: list[str] = Field(
        default_factory=lambda: [CURRENT_RISK_POLICY_VERSION],
        min_length=1,
        max_length=10,
    )
    max_samples: int = Field(default=500, ge=1, le=500)

    @model_validator(mode="after")
    def _valid_window(self) -> HistoricalRiskQuery:
        if self.window_end <= self.window_start:
            raise ValueError("window_end deve ser posterior a window_start")
        return self


class HistoricalSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    pattern_type: PatternType
    lifecycle: MemoryLifecycle
    task_type: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_count: int = Field(..., ge=0)
    updated_at: datetime
    operational_memory_policy_version: str
    risk_policy_versions: list[str] = Field(default_factory=list)
    outcome_class: str


class ExcludedHistoricalSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    reason_code: str
    observed_policy_versions: list[str] = Field(default_factory=list)


class HistoricalRiskSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    project_id: str
    policy_version: Literal["historical-risk-v1"] = HISTORICAL_RISK_POLICY_VERSION
    risk_policy_versions: list[str]
    window_start: datetime
    window_end: datetime
    filters: dict[str, object] = Field(default_factory=dict)
    sample_size: int = Field(..., ge=0)
    excluded_count: int = Field(..., ge=0)
    outcomes: dict[str, int] = Field(default_factory=dict)
    average_confidence: float = Field(..., ge=0.0, le=1.0)
    generalizable: bool = False
    small_sample_warning: bool = True
    samples: list[HistoricalSample] = Field(default_factory=list)
    excluded_samples: list[ExcludedHistoricalSample] = Field(default_factory=list)
    training_performed: Literal[False] = False


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1, max_length=128)
    request: RiskRequest
    actual_risk: bool
    severe_actual: bool = False


class HistoricalBenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str | None = Field(default=None, min_length=3, max_length=128)
    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    window_start: datetime
    window_end: datetime
    risk_policy_version: Literal["pre-execution-risk-v1"] = CURRENT_RISK_POLICY_VERSION
    cases: list[BenchmarkCase] = Field(..., min_length=1, max_length=100)

    @model_validator(mode="after")
    def _consistent_scope(self) -> HistoricalBenchmarkRequest:
        if self.window_end <= self.window_start:
            raise ValueError("window_end deve ser posterior a window_start")
        project = self.project_id.strip().lower()
        if any(item.request.project_id.strip().lower() != project for item in self.cases):
            raise ValueError("todos os benchmark cases devem pertencer ao mesmo projeto")
        if any(item.request.producer != self.producer for item in self.cases):
            raise ValueError("producer dos cases deve corresponder ao benchmark")
        return self


class CasePrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    predicted_risk: bool | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)


class StrategyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: RiskStrategy
    sample_size: int = Field(..., ge=0)
    abstentions: int = Field(..., ge=0)
    true_positive: int = Field(..., ge=0)
    false_positive: int = Field(..., ge=0)
    true_negative: int = Field(..., ge=0)
    false_negative: int = Field(..., ge=0)
    severe_false_negative: int = Field(..., ge=0)
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    severity_weighted_errors: float = Field(..., ge=0.0)
    calibration_error: float = Field(..., ge=0.0, le=1.0)
    review_abstention_rate: float = Field(..., ge=0.0, le=1.0)
    predictions: list[CasePrediction] = Field(default_factory=list)


class HistoricalBenchmarkResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str
    project_id: str
    policy_version: Literal["historical-risk-v1"] = HISTORICAL_RISK_POLICY_VERSION
    risk_policy_version: Literal["pre-execution-risk-v1"] = CURRENT_RISK_POLICY_VERSION
    historical_summary: HistoricalRiskSummary
    strategies: list[StrategyMetrics]
    recommended_strategy: str
    recommendation_basis: list[str]
    reproducible: Literal[True] = True
    training_performed: Literal[False] = False
