import asyncio

from app.core.config import settings
from app.modules.providers.base import (
    BaseAIProvider,
    ProviderConfigError,
    ProviderExecutionError,
    ProviderResponse,
)


class OpenAIProvider(BaseAIProvider):
    name = "openai"
    label = "OpenAI"
    default_model = settings.openai_model

    @property
    def is_configured(self) -> bool:
        return bool(settings.openai_api_key)

    async def generate_response(
        self,
        message: str,
        mode: str,
        model: str,
        system_prompt: str | None = None,
    ) -> ProviderResponse:
        if not self.is_configured:
            raise ProviderConfigError("OPENAI_API_KEY não configurada.")

        try:
            from openai import OpenAI

            prompt = self.build_prompt(message, mode, system_prompt)
            selected_model = model

            def run_request() -> str:
                client = OpenAI(api_key=settings.openai_api_key)
                response = client.responses.create(
                    model=selected_model,
                    input=prompt,
                )
                return getattr(response, "output_text", "") or ""

            text = await asyncio.to_thread(run_request)

            if not text.strip():
                raise ProviderExecutionError("OpenAI respondeu sem texto utilizável.")

            return ProviderResponse(answer=text, provider=self.name, model=selected_model)
        except ProviderExecutionError:
            raise
        except Exception as error:
            raise ProviderExecutionError(f"Falha no OpenAIProvider: {error}") from error
