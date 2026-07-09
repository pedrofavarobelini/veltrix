from pydantic import BaseModel, Field

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


class TechnicalReportInput(BaseModel):
    """Relatório técnico enviado por payload (nenhuma leitura de repositório).

    Relatórios NÃO treinam IA: alimentam apenas sinais determinísticos e a
    futura memória técnica. Nenhuma persistência ocorre nesta fundação.
    """

    project_id: str = Field(..., min_length=1)
    report_type: str = Field(..., min_length=1)
    source: str | None = None
    run_id: str | None = None
    branch: str | None = None
    commit: str | None = None
    status: str = Field(..., min_length=1)
    summary: str | None = None
    safety_flags: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    suggested_fixes: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    created_at: str | None = None
    metadata: dict | None = None


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
