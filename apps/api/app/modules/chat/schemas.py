from pydantic import BaseModel, Field


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


class ProviderInfo(BaseModel):
    name: str
    label: str
    default_model: str
    configured: bool
    real_provider: bool
