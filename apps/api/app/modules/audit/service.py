import uuid
from datetime import datetime, timezone

from app.modules.audit.schemas import AuditMetadata
from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    OriginClaimResult,
)
from app.modules.provider_binding.schemas import SelectedProviderModel


class AuditService:
    def create(
        self,
        origin_system: str,
        task_type: str,
        provider_requested: str,
        criticality: str,
        caller: AuthenticatedCallerContext | None = None,
        origin_claim: OriginClaimResult | None = None,
        provider_selection_mode: str | None = None,
        binding: SelectedProviderModel | None = None,
    ) -> AuditMetadata:
        """Cria a auditoria da requisição.

        Registra identidade autenticada e origem declarada como campos
        distintos, sem nunca gravar o valor da credencial.
        """
        return AuditMetadata(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            origin_system=origin_system,
            task_type=task_type,
            provider_requested=provider_requested,
            fallback_used=None,
            criticality=criticality,
            credential_id=caller.credential_id if caller is not None else None,
            authenticated=caller.authenticated if caller is not None else False,
            identity_strength=(
                caller.identity_strength.value if caller is not None else None
            ),
            project_id_authenticated=(
                origin_claim.identity_project_id if origin_claim is not None else None
            ),
            caller_role=caller.caller_role.value if caller is not None else None,
            environment=caller.environment if caller is not None else None,
            origin_system_declared=origin_system,
            origin_validation=(
                origin_claim.validation.value if origin_claim is not None else None
            ),
            provider_selection_mode=provider_selection_mode,
            model_requested=binding.requested_model if binding is not None else None,
            model_selected=binding.model_id if binding is not None else None,
            model_source=binding.model_source.value if binding is not None else None,
        )


audit_service = AuditService()
