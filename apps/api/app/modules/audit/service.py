import uuid
from datetime import datetime, timezone

from app.modules.audit.schemas import AuditMetadata


class AuditService:
    def create(
        self,
        origin_system: str,
        task_type: str,
        provider_requested: str,
        criticality: str,
    ) -> AuditMetadata:
        return AuditMetadata(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            origin_system=origin_system,
            task_type=task_type,
            provider_requested=provider_requested,
            fallback_used=None,
            criticality=criticality,
        )


audit_service = AuditService()
