from pydantic import BaseModel, Field

from app.modules.artifacts.schemas import ArtifactInput
from app.modules.qa_response.schemas import QAResponseSkeleton


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    mode: str = "tecnico"
    provider: str = "mock"
    model: str | None = None
    system_prompt: str | None = None
    task_type: str = "general_chat"
    origin_system: str = "pedrocore"
    context: dict | None = None
    metadata: dict | None = None
    artifacts: list[ArtifactInput] | None = None
    allow_real_provider: bool = False
    # ECOSYSTEM-INTELLIGENCE-SUITE-01: opt-ins explícitos, sempre False por padrão.
    allow_local_model: bool = False
    context_from_memory: bool = False


class ChatResponse(BaseModel):
    answer: str
    provider: str
    model: str
    mode: str
    requested_provider: str
    fallback_used: bool = False
    error: str | None = None
    task_type: str = "general_chat"
    origin_system: str = "pedrocore"
    task_criticality: str = "low"
    requires_structured_response: bool = False
    task_warnings: list[str] = Field(default_factory=list)
    project_id: str = "pedrocore"
    project_read_only: bool = True
    project_can_execute_commands: bool = False
    project_can_write_files: bool = False
    response_style: str = "free_text"
    audit_id: str | None = None
    audit_timestamp: str | None = None
    task_allowed_for_project: bool = True
    artifact_count: int = 0
    artifact_types: list[str] = Field(default_factory=list)
    artifact_warnings: list[str] = Field(default_factory=list)
    qa_skeleton: QAResponseSkeleton | None = None
    warning_codes: list[str] = Field(default_factory=list)
    safe_mode_blocked: bool = False
    status: str = "ok"
    blocked_reason: str | None = None
    error_code: str | None = None


class ProviderInfo(BaseModel):
    name: str
    label: str
    default_model: str
    configured: bool
    real_provider: bool
