from pydantic import BaseModel


class AuditMetadata(BaseModel):
    audit_id: str
    timestamp: str
    origin_system: str
    task_type: str
    provider_requested: str
    fallback_used: bool | None = None
    criticality: str
