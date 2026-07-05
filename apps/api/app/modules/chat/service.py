from app.modules.chat.schemas import ChatRequest, ChatResponse
from app.modules.orchestration.service import orchestration_service
from app.modules.providers.registry import provider_registry


class ChatService:
    """Camada fina de compatibilidade do /api/chat sobre o pipeline central de orquestração."""

    async def send_message(self, payload: ChatRequest) -> ChatResponse:
        outcome = await orchestration_service.execute(payload)

        return ChatResponse(
            answer=outcome.answer,
            provider=outcome.provider_used,
            model=outcome.model,
            mode=outcome.mode,
            requested_provider=outcome.provider_requested,
            fallback_used=outcome.fallback_used,
            error=outcome.error,
            task_type=outcome.task_type,
            origin_system=outcome.origin_system,
            task_criticality=outcome.task_criticality,
            requires_structured_response=outcome.requires_structured_response,
            task_warnings=outcome.task_warnings,
            project_id=outcome.project_id,
            project_read_only=outcome.project_read_only,
            project_can_execute_commands=outcome.project_can_execute_commands,
            project_can_write_files=outcome.project_can_write_files,
            response_style=outcome.response_style,
            audit_id=outcome.audit.audit_id,
            audit_timestamp=outcome.audit.timestamp,
            task_allowed_for_project=outcome.task_allowed_for_project,
            artifact_count=outcome.artifact_count,
            artifact_types=outcome.artifact_types,
            artifact_warnings=outcome.artifact_warnings,
            qa_skeleton=outcome.qa_skeleton,
            warning_codes=outcome.warning_codes,
            safe_mode_blocked=outcome.safe_mode_blocked,
            status=outcome.status,
            blocked_reason=outcome.blocked_reason,
            error_code=outcome.error_code,
        )

    def list_providers(self) -> list[dict[str, object]]:
        return provider_registry.list_providers()
