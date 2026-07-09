from app.modules.providers.base import BaseAIProvider
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.local_model_provider import local_model_provider
from app.modules.providers.mock_provider import MockProvider
from app.modules.providers.openai_provider import OpenAIProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseAIProvider] = {
            "mock": MockProvider(),
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "claude": ClaudeProvider(),
            "deepseek": DeepSeekProvider(),
            "grok": GrokProvider(),
            # Local generative opt-in (default OFF): real_provider=False,
            # sem chave externa, configured=false sem flag explícita.
            "local_model": local_model_provider,
        }

    def get(self, name: str | None) -> BaseAIProvider | None:
        if not name:
            return self._providers["mock"]
        return self._providers.get(name.lower())

    def mock(self) -> BaseAIProvider:
        return self._providers["mock"]

    def list_providers(self) -> list[dict[str, object]]:
        providers = [
            {
                "name": provider.name,
                "label": provider.label,
                "default_model": provider.default_model,
                "configured": provider.is_configured,
                "real_provider": provider.real_provider,
            }
            for provider in self._providers.values()
        ]
        providers.extend(
            [
                {
                    "name": "local_qa",
                    "label": "Local QA",
                    "default_model": "local-qa-v1",
                    "configured": True,
                    "real_provider": False,
                },
                {
                    "name": "auto",
                    "label": "Auto",
                    "default_model": "auto",
                    "configured": self._providers["gemini"].is_configured,
                    "real_provider": True,
                },
            ]
        )
        return providers


provider_registry = ProviderRegistry()
