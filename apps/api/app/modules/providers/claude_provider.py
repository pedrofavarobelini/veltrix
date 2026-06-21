import asyncio

from app.core.config import settings
from app.modules.providers.base import (
    BaseAIProvider,
    ProviderConfigError,
    ProviderExecutionError,
    ProviderResponse,
)


class ClaudeProvider(BaseAIProvider):
    name = "claude"
    label = "Claude"
    default_model = settings.anthropic_model

    @property
    def is_configured(self) -> bool:
        return bool(settings.anthropic_api_key)

    async def generate_response(
        self,
        message: str,
        mode: str,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> ProviderResponse:
        if not self.is_configured:
            raise ProviderConfigError("ANTHROPIC_API_KEY não configurada.")

        try:
            import anthropic

            prompt = self.build_prompt(message, mode, system_prompt)
            selected_model = model or self.default_model

            def run_request() -> str:
                client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                response = client.messages.create(
                    model=selected_model,
                    max_tokens=1200,
                    messages=[{"role": "user", "content": prompt}],
                )
                parts: list[str] = []
                for block in response.content:
                    text = getattr(block, "text", None)
                    if text:
                        parts.append(text)
                return "\n".join(parts)

            text = await asyncio.to_thread(run_request)

            if not text.strip():
                raise ProviderExecutionError("Claude respondeu sem texto utilizável.")

            return ProviderResponse(answer=text, provider=self.name, model=selected_model)
        except ProviderExecutionError:
            raise
        except Exception as error:
            raise ProviderExecutionError(f"Falha no ClaudeProvider: {error}") from error
