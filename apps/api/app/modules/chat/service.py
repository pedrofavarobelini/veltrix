from app.core.config import settings
from app.modules.artifacts.schemas import ArtifactProcessingResult
from app.modules.artifacts.service import artifact_service
from app.modules.audit.schemas import AuditMetadata
from app.modules.audit.service import audit_service
from app.modules.chat.schemas import ChatRequest, ChatResponse
from app.modules.project_context.schemas import ProjectContext, TaskPolicyResult
from app.modules.project_context.service import project_context_resolver
from app.modules.prompt_builder.schemas import PromptBuildInput
from app.modules.prompt_builder.service import prompt_builder
from app.modules.providers.registry import provider_registry
from app.modules.qa_response.service import QA_NO_ARTIFACTS_WARNING, qa_response_service
from app.modules.task_router.schemas import TaskStrategy
from app.modules.task_router.service import (
    CRITICAL_TASK_TYPES,
    FALLBACK_CRITICAL_WARNING,
    MOCK_CRITICAL_WARNING,
    task_router,
)


class ChatService:
    async def send_message(self, payload: ChatRequest) -> ChatResponse:
        strategy = task_router.resolve(payload.task_type)
        project = project_context_resolver.resolve(payload.origin_system)
        policy = project_context_resolver.evaluate_task_policy(project, strategy.task_type)
        artifacts_result = artifact_service.process(payload.artifacts)
        requested_provider = (payload.provider or settings.default_provider).lower()

        audit = audit_service.create(
            origin_system=payload.origin_system,
            task_type=strategy.task_type,
            provider_requested=requested_provider,
            criticality=strategy.criticality,
        )

        prompt = prompt_builder.build(
            PromptBuildInput(
                message=payload.message,
                mode=payload.mode,
                system_prompt=payload.system_prompt,
                strategy=strategy,
                project=project,
                origin_system=payload.origin_system,
                context=payload.context,
                metadata=payload.metadata,
                artifacts_text_block=artifacts_result.text_block,
            )
        )

        provider = provider_registry.get(requested_provider)

        if provider is None:
            return await self._fallback(
                payload=payload,
                requested_provider=requested_provider,
                error=f"Provider não suportado: {requested_provider}",
                strategy=strategy,
                project=project,
                policy=policy,
                artifacts_result=artifacts_result,
                audit=audit,
                enriched_system_prompt=prompt.enriched_system_prompt,
            )

        try:
            result = await provider.generate_response(
                message=payload.message,
                mode=payload.mode,
                model=payload.model,
                system_prompt=prompt.enriched_system_prompt,
            )

            audit.fallback_used = False

            return ChatResponse(
                answer=result.answer,
                provider=result.provider,
                model=result.model,
                mode=payload.mode,
                requested_provider=requested_provider,
                fallback_used=False,
                error=None,
                task_type=strategy.task_type,
                origin_system=payload.origin_system,
                task_criticality=strategy.criticality,
                requires_structured_response=strategy.requires_structured_response,
                task_warnings=self._task_warnings(
                    strategy=strategy,
                    project=project,
                    policy=policy,
                    artifacts_result=artifacts_result,
                    provider_name=result.provider,
                    fallback_used=False,
                ),
                project_id=project.project_id,
                project_read_only=project.read_only,
                project_can_execute_commands=project.can_execute_commands,
                project_can_write_files=project.can_write_files,
                response_style=strategy.response_style,
                audit_id=audit.audit_id,
                audit_timestamp=audit.timestamp,
                task_allowed_for_project=policy.allowed,
                artifact_count=artifacts_result.count,
                artifact_types=artifacts_result.types,
                artifact_warnings=artifacts_result.warnings,
                qa_skeleton=qa_response_service.build_skeleton(
                    task_type=strategy.task_type,
                    fallback_used=False,
                    artifacts_result=artifacts_result,
                ),
            )
        except Exception as error:
            return await self._fallback(
                payload=payload,
                requested_provider=requested_provider,
                error=str(error),
                strategy=strategy,
                project=project,
                policy=policy,
                artifacts_result=artifacts_result,
                audit=audit,
                enriched_system_prompt=prompt.enriched_system_prompt,
            )

    async def _fallback(
        self,
        payload: ChatRequest,
        requested_provider: str,
        error: str,
        strategy: TaskStrategy,
        project: ProjectContext,
        policy: TaskPolicyResult,
        artifacts_result: ArtifactProcessingResult,
        audit: AuditMetadata,
        enriched_system_prompt: str,
    ) -> ChatResponse:
        mock = provider_registry.mock()
        fallback_message = (
            f"Fallback acionado. O provider '{requested_provider}' falhou ou não está configurado.\n\n"
            f"Erro técnico: {error}\n\n"
            f"Mensagem original: {payload.message}"
        )

        result = await mock.generate_response(
            message=fallback_message,
            mode=payload.mode,
            model="mock-v1",
            system_prompt=enriched_system_prompt,
        )

        audit.fallback_used = True

        return ChatResponse(
            answer=result.answer,
            provider="mock",
            model="mock-v1",
            mode=payload.mode,
            requested_provider=requested_provider,
            fallback_used=True,
            error=error,
            task_type=strategy.task_type,
            origin_system=payload.origin_system,
            task_criticality=strategy.criticality,
            requires_structured_response=strategy.requires_structured_response,
            task_warnings=self._task_warnings(
                strategy=strategy,
                project=project,
                policy=policy,
                artifacts_result=artifacts_result,
                provider_name="mock",
                fallback_used=True,
            ),
            project_id=project.project_id,
            project_read_only=project.read_only,
            project_can_execute_commands=project.can_execute_commands,
            project_can_write_files=project.can_write_files,
            response_style=strategy.response_style,
            audit_id=audit.audit_id,
            audit_timestamp=audit.timestamp,
            task_allowed_for_project=policy.allowed,
            artifact_count=artifacts_result.count,
            artifact_types=artifacts_result.types,
            artifact_warnings=artifacts_result.warnings,
            qa_skeleton=qa_response_service.build_skeleton(
                task_type=strategy.task_type,
                fallback_used=True,
                artifacts_result=artifacts_result,
            ),
        )

    def _task_warnings(
        self,
        strategy: TaskStrategy,
        project: ProjectContext,
        policy: TaskPolicyResult,
        artifacts_result: ArtifactProcessingResult,
        provider_name: str,
        fallback_used: bool,
    ) -> list[str]:
        warnings = (
            list(strategy.warnings)
            + list(project.warnings)
            + list(policy.warnings)
            + list(artifacts_result.warnings)
        )

        if strategy.task_type in CRITICAL_TASK_TYPES and artifacts_result.count == 0:
            warnings.append(QA_NO_ARTIFACTS_WARNING)

        if fallback_used and strategy.task_type in CRITICAL_TASK_TYPES:
            warnings.append(FALLBACK_CRITICAL_WARNING)
        elif provider_name == "mock" and not strategy.allow_mock:
            warnings.append(MOCK_CRITICAL_WARNING)

        return warnings

    def list_providers(self) -> list[dict[str, object]]:
        return provider_registry.list_providers()
