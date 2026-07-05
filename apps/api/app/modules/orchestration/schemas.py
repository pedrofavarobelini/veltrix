from pydantic import BaseModel, Field

from app.modules.audit.schemas import AuditMetadata
from app.modules.contracts.codes import WarningItem
from app.modules.qa_response.schemas import QAResponseSkeleton, ReleaseGateResult


class OrchestrationOutcome(BaseModel):
    """Resultado interno completo do pipeline, consumido por /api/chat e /api/orchestrate."""

    answer: str
    provider_requested: str
    provider_used: str
    model: str
    mode: str
    fallback_used: bool = False
    safe_mode_blocked: bool = False
    error: str | None = None
    task_type: str
    origin_system: str
    task_criticality: str
    requires_structured_response: bool
    response_style: str
    project_id: str
    project_read_only: bool
    project_can_execute_commands: bool
    project_can_write_files: bool
    task_allowed_for_project: bool
    artifact_count: int
    artifact_types: list[str] = Field(default_factory=list)
    artifact_warnings: list[str] = Field(default_factory=list)
    qa_skeleton: QAResponseSkeleton | None = None
    release_gate: ReleaseGateResult | None = None
    warning_items: list[WarningItem] = Field(default_factory=list)
    audit: AuditMetadata
    status: str = "ok"
    blocked_reason: str | None = None
    error_code: str | None = None

    @property
    def task_warnings(self) -> list[str]:
        return [item.message for item in self.warning_items]

    @property
    def warning_codes(self) -> list[str]:
        return [item.code for item in self.warning_items]


class OrchestrateResponse(BaseModel):
    """Contrato de resposta do endpoint POST /api/orchestrate."""

    status: str = "ok"
    answer: str
    task_type: str
    origin_system: str
    provider_requested: str
    provider_used: str
    model: str
    mode: str
    fallback_used: bool = False
    safe_mode_blocked: bool = False
    allow_real_provider: bool = False
    warning_codes: list[str] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    task_warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    blocked_reason: str | None = None
    project_id: str = "pedrocore"
    task_allowed_for_project: bool = True
    artifact_count: int = 0
    artifact_types: list[str] = Field(default_factory=list)
    artifact_warnings: list[str] = Field(default_factory=list)
    qa: QAResponseSkeleton | None = None
    release_gate: ReleaseGateResult | None = None
    audit: AuditMetadata
