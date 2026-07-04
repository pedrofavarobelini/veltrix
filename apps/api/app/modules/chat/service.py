from app.core.config import settings
from app.modules.chat.schemas import ChatRequest, ChatResponse
from app.modules.providers.registry import provider_registry
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
        requested_provider = (payload.provider or settings.default_provider).lower()
        provider = provider_registry.get(requested_provider)

        if provider is None:
            return await self._fallback(
                payload=payload,
                requested_provider=requested_provider,
                error=f"Provider não suportado: {requested_provider}",
                strategy=strategy,
            )

        try:
            result = await provider.generate_response(
                message=payload.message,
                mode=payload.mode,
                model=payload.model,
                system_prompt=payload.system_prompt,
            )

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
                    provider_name=result.provider,
                    fallback_used=False,
                ),
            )
        except Exception as error:
            return await self._fallback(
                payload=payload,
                requested_provider=requested_provider,
                error=str(error),
                strategy=strategy,
            )

    async def _fallback(
        self,
        payload: ChatRequest,
        requested_provider: str,
        error: str,
        strategy: TaskStrategy,
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
            system_prompt=payload.system_prompt,
        )

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
                provider_name="mock",
                fallback_used=True,
            ),
        )

    def _task_warnings(
        self,
        strategy: TaskStrategy,
        provider_name: str,
        fallback_used: bool,
    ) -> list[str]:
        warnings = list(strategy.warnings)

        if fallback_used and strategy.task_type in CRITICAL_TASK_TYPES:
            warnings.append(FALLBACK_CRITICAL_WARNING)
        elif provider_name == "mock" and not strategy.allow_mock:
            warnings.append(MOCK_CRITICAL_WARNING)

        return warnings

    def list_providers(self) -> list[dict[str, object]]:
        return provider_registry.list_providers()
