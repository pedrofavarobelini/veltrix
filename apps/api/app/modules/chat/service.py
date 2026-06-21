from app.core.config import settings
from app.modules.chat.schemas import ChatRequest, ChatResponse
from app.modules.providers.registry import provider_registry


class ChatService:
    async def send_message(self, payload: ChatRequest) -> ChatResponse:
        requested_provider = (payload.provider or settings.default_provider).lower()
        provider = provider_registry.get(requested_provider)

        if provider is None:
            return await self._fallback(
                payload=payload,
                requested_provider=requested_provider,
                error=f"Provider não suportado: {requested_provider}",
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
            )
        except Exception as error:
            return await self._fallback(
                payload=payload,
                requested_provider=requested_provider,
                error=str(error),
            )

    async def _fallback(
        self,
        payload: ChatRequest,
        requested_provider: str,
        error: str,
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
        )

    def list_providers(self) -> list[dict[str, object]]:
        return provider_registry.list_providers()
