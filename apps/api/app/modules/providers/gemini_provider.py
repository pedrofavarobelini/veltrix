import asyncio

from app.core.config import settings
from app.modules.providers.base import (
    BaseAIProvider,
    ProviderConfigError,
    ProviderExecutionError,
    ProviderResponse,
)


class GeminiProvider(BaseAIProvider):
    name = "gemini"
    label = "Gemini"
    default_model = settings.gemini_model

    @property
    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key)

    async def generate_response(
        self,
        message: str,
        mode: str,
        model: str,
        system_prompt: str | None = None,
    ) -> ProviderResponse:
        if not self.is_configured:
            raise ProviderConfigError("GEMINI_API_KEY não configurada.")

        try:
            from google import genai

            prompt = self.build_prompt(message, mode, system_prompt)
            selected_model = model

            def run_request() -> str:
                client = genai.Client(api_key=settings.gemini_api_key)
                response = client.models.generate_content(
                    model=selected_model,
                    contents=prompt,
                )
                return getattr(response, "text", "") or ""

            text = await asyncio.to_thread(run_request)

            if not text.strip():
                raise ProviderExecutionError("Gemini respondeu sem texto utilizável.")

            return ProviderResponse(answer=text, provider=self.name, model=selected_model)
        except ProviderExecutionError:
            raise
        except Exception as error:
            raise ProviderExecutionError(f"Falha no GeminiProvider: {error}") from error
