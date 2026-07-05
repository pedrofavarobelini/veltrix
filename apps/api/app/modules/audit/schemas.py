from pydantic import BaseModel


class AuditMetadata(BaseModel):
    audit_id: str
    timestamp: str
    origin_system: str
    task_type: str
    provider_requested: str
    fallback_used: bool | None = None
    criticality: str
    provider_used: str | None = None
    safe_mode_blocked: bool = False
    status: str = "ok"
    latency_ms: float | None = None
    risk_level: str | None = None
    can_advance: bool | None = None
