from pydantic import BaseModel, Field

from app.modules.contracts.codes import WarningItem
from app.modules.evaluation.schemas import EvaluationResult
from app.modules.report_intelligence.schemas import (
    IntelligenceReportEnvelopeV2,
    ReportSignal,
    TechnicalReportInput,
)


class ReportMemoryEntry(BaseModel):
    """Entrada de memória técnica derivada de um relatório ingerido.

    Memória técnica NÃO é treinamento: guarda sinais/histórico consultável,
    nunca altera comportamento do modelo automaticamente.
    """

    memory_id: str
    report_id: str | None = None
    schema_version: str = "1"
    producer: str | None = None
    project_id: str
    report_type: str
    source_run_id: str | None = None
    conversation_id: str | None = None
    source_commit: str | None = None
    branch: str | None = None
    status: str
    summary: str | None = None
    signals: list[ReportSignal] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)
    completed_milestones: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    source_signals: list[dict] = Field(default_factory=list)
    evidence: list[str | dict] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict | None = None


class ReportMemoryQuery(BaseModel):
    project_id: str = Field(..., min_length=1)
    report_type: str | None = None
    limit: int = Field(default=10, ge=1, le=50)
    include_signals: bool = True
    include_risks: bool = True
    include_next_steps: bool = True


class ProjectMemorySnapshot(BaseModel):
    """Snapshot agregado da memória técnica de um projeto."""

    project_id: str
    last_known_status: str = "unknown"
    last_report_at: str | None = None
    latest_commit: str | None = None
    latest_branch: str | None = None
    completed_milestones: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)
    recurring_signals: list[str] = Field(default_factory=list)
    next_recommended_steps: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    source_count: int = 0


class ReportAnalyzeResponse(BaseModel):
    """Resposta de POST /api/reports/analyze — análise sem persistência."""

    status: str = "ok"
    report: TechnicalReportInput
    signals: list[ReportSignal] = Field(default_factory=list)
    evaluation: EvaluationResult
    warnings: list[WarningItem] = Field(default_factory=list)


class ReportIngestResponse(BaseModel):
    """Resposta de POST /api/reports/ingest."""

    status: str = "ok"
    stored: bool = False
    duplicate: bool = False
    memory_id: str | None = None
    snapshot: ProjectMemorySnapshot | None = None
    signals: list[ReportSignal] = Field(default_factory=list)
    evaluation: EvaluationResult | None = None
    warnings: list[WarningItem] = Field(default_factory=list)


class ReportAnalyzeV2Response(BaseModel):
    status: str = "ok"
    report: IntelligenceReportEnvelopeV2
    signals: list[ReportSignal] = Field(default_factory=list)
    evaluation: EvaluationResult
    warnings: list[WarningItem] = Field(default_factory=list)


class ReportIngestV2Response(BaseModel):
    status: str = "ok"
    stored: bool = False
    duplicate: bool = False
    report_id: str
    memory_id: str | None = None
    snapshot: ProjectMemorySnapshot | None = None
    signals: list[ReportSignal] = Field(default_factory=list)
    evaluation: EvaluationResult | None = None
    warnings: list[WarningItem] = Field(default_factory=list)


class ProjectMemorySummaryResponse(BaseModel):
    """Resposta de GET /api/project-memory/{project_id}/summary."""

    status: str = "ok"
    snapshot: ProjectMemorySnapshot | None = None
    warnings: list[WarningItem] = Field(default_factory=list)
