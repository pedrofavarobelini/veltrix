from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SIGNAL_TYPES = {
    "qa_passed",
    "qa_failed",
    "provider_real_blocked",
    "provider_real_used",
    "database_safety_ok",
    "database_safety_risk",
    "smoke_coverage",
    "full_coverage",
    "documentation_gap",
    "architecture_risk",
    "release_gate_blocked",
    "release_gate_passed",
    "next_step",
    "human_review_required",
}

SEVERITIES = {"info", "low", "medium", "high", "critical"}
REPORT_SCHEMA_VERSION_V2 = "2.0"


class IntelligenceReportType(str, Enum):
    INTERACTION_QUALITY = "interaction_quality"
    QA_EVIDENCE = "qa_evidence"
    RISK_ANALYSIS = "risk_analysis"
    EXECUTION_OUTCOME = "execution_outcome"


class TechnicalReportInput(BaseModel):
    """Relatório técnico enviado por payload (nenhuma leitura de repositório).

    Relatórios NÃO treinam IA: alimentam apenas sinais determinísticos e a
    futura memória técnica. Nenhuma persistência ocorre nesta fundação.
    """

    project_id: str = Field(..., min_length=1)
    report_type: str = Field(..., min_length=1)
    report_id: str | None = None
    source: str | None = None
    run_id: str | None = None
    conversation_id: str | None = None
    branch: str | None = None
    commit: str | None = None
    status: str = Field(..., min_length=1)
    summary: str | None = None
    safety_flags: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    signals: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str | dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None
    metadata: dict[str, Any] | None = None


class ReportPayloadBase(BaseModel):
    """Payload tipado V2. Extensões devem viver em `metadata`, não como mass assignment."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., min_length=1)
    legacy_report_type: str | None = None
    source: str | None = None
    branch: str | None = None
    commit: str | None = None
    summary: str | None = None
    safety_flags: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    signals: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[str | dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InteractionQualityPayload(ReportPayloadBase):
    feedback: Literal["positive", "negative", "neutral", "unknown"] = "unknown"
    quality_signals: list[str] = Field(default_factory=list)


class QaEvidencePayload(ReportPayloadBase):
    test_scope: str | None = None
    passed: int | None = Field(default=None, ge=0)
    failed: int | None = Field(default=None, ge=0)
    skipped: int | None = Field(default=None, ge=0)


class RiskAnalysisPayload(ReportPayloadBase):
    risk_level: str | None = None
    risk_dimensions: dict[str, float] = Field(default_factory=dict)
    policy_version: str | None = None


class ExecutionOutcomePayload(ReportPayloadBase):
    outcome: str | None = None
    scope_deviation: bool = False
    qa_passed: bool | None = None


TypedReportPayload = (
    InteractionQualityPayload
    | QaEvidencePayload
    | RiskAnalysisPayload
    | ExecutionOutcomePayload
)

_PAYLOAD_BY_REPORT_TYPE: dict[IntelligenceReportType, type[ReportPayloadBase]] = {
    IntelligenceReportType.INTERACTION_QUALITY: InteractionQualityPayload,
    IntelligenceReportType.QA_EVIDENCE: QaEvidencePayload,
    IntelligenceReportType.RISK_ANALYSIS: RiskAnalysisPayload,
    IntelligenceReportType.EXECUTION_OUTCOME: ExecutionOutcomePayload,
}


def payload_model_for(
    report_type: IntelligenceReportType,
) -> type[ReportPayloadBase]:
    return _PAYLOAD_BY_REPORT_TYPE[report_type]


class IntelligenceReportEnvelopeV2(BaseModel):
    """Common Envelope V2 + payload selecionado estritamente por `report_type`."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["2.0"] = REPORT_SCHEMA_VERSION_V2
    report_id: str = Field(..., min_length=3, max_length=128)
    report_type: IntelligenceReportType
    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    run_id: str | None = Field(default=None, max_length=128)
    conversation_id: str | None = Field(default=None, max_length=128)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    payload: TypedReportPayload

    @model_validator(mode="before")
    @classmethod
    def _select_typed_payload(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        try:
            report_type = IntelligenceReportType(value.get("report_type"))
        except (TypeError, ValueError):
            return value
        payload = value.get("payload")
        if isinstance(payload, ReportPayloadBase):
            return value
        parsed = dict(value)
        parsed["payload"] = payload_model_for(report_type).model_validate(payload)
        return parsed

    @model_validator(mode="after")
    def _payload_matches_report_type(self) -> IntelligenceReportEnvelopeV2:
        expected = payload_model_for(self.report_type)
        if not isinstance(self.payload, expected):
            raise ValueError("payload não corresponde ao report_type declarado")
        return self


class ReportSignal(BaseModel):
    """Sinal determinístico extraído de um relatório técnico."""

    project_id: str
    report_type: str
    signal_type: str
    severity: str = "info"
    summary: str
    evidence: str | None = None
    confidence: float = 0.5
    source_run_id: str | None = None
    source_commit: str | None = None
    created_at: str | None = None


class ReportMemorySummary(BaseModel):
    """Resumo agregado (memória técnica futura) de um projeto — sem persistência."""

    project_id: str
    last_known_status: str = "unknown"
    important_signals: list[ReportSignal] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)
    completed_milestones: list[str] = Field(default_factory=list)
    next_recommended_steps: list[str] = Field(default_factory=list)
    updated_at: str | None = None
