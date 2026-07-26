from typing import Any

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    stage: str
    status: str
    detail: str | None = None
    offset_ms: float | None = None


class ProviderAttempt(BaseModel):
    provider: str
    result: str
    detail: str | None = None


class ExecutionRecord(BaseModel):
    execution_id: str
    audit_id: str
    timestamp: str
    origin_system: str
    task: str
    status: str
    payload_sanitized: dict[str, Any] = Field(default_factory=dict)
    removed_fields: list[str] = Field(default_factory=list)
    # Identidade autenticada do caller, sem segredos (Etapa 2).
    caller: dict[str, Any] | None = None
    # Provider/model planejado pelo binding vs. efetivamente executado (Etapa 3).
    binding: dict[str, Any] | None = None
    provider_requested: str | None = None
    provider_selected: str | None = None
    provider_effective: str | None = None
    provider_attempts: list[ProviderAttempt] = Field(default_factory=list)
    fallback: bool = False
    fallback_reason: str | None = None
    duration_ms: float = 0.0
    public_response: str | None = None
    release_gate: dict[str, Any] | None = None
    evaluation: dict[str, Any] | None = None
    signals: list[dict[str, Any]] = Field(default_factory=list)
    memory_consulted: bool = False
    memory_created: bool = False
    memory_id: str | None = None
    error: str | None = None
    retry: dict[str, Any] = Field(default_factory=dict)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    result_returned: dict[str, Any] = Field(default_factory=dict)


class ExecutionSummary(BaseModel):
    execution_id: str
    audit_id: str
    timestamp: str
    origin_system: str
    task: str
    status: str
    provider_effective: str | None = None
    fallback: bool = False
    duration_ms: float = 0.0


class ExecutionListResponse(BaseModel):
    enabled: bool
    mode: str
    total: int
    items: list[ExecutionSummary] = Field(default_factory=list)


class ObservabilityStatusResponse(BaseModel):
    enabled: bool
    mode: str
    storage: str = "in_memory_ring_buffer"
    max_entries: int
    local_only: bool = True
    training_implemented: bool = False
    notice: str


class GeminiSmokeRequest(BaseModel):
    synthetic_payload: str
    confirm_network: bool = False
    confirm_possible_cost: bool = False
    confirm_key_not_compromised: bool = False


class GeminiSmokeResponse(BaseModel):
    status: str
    executed: bool
    call_count: int = 0
    provider: str = "gemini"
    model: str | None = None
    fallback: bool = False
    reason: str | None = None
    public_response: str | None = None
    notices: list[str] = Field(default_factory=list)
