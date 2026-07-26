from types import SimpleNamespace

from app.modules.providers.base import BaseAIProvider


class MockProvider(BaseAIProvider):
    name = "mock"
    label = "Mock"
    default_model = "mock-v1"
    real_provider = False

    @property
    def is_configured(self) -> bool:
        return True

    async def generate_response(
        self,
        message: str,
        mode: str,
        model: str,
        system_prompt: str | None = None
    ):
        selected_model = model

        if mode == "resumido":
            answer = (
                "Resumo: entendi sua solicitacao. "
                "Na versao real, a IA respondera de forma mais objetiva e contextual."
            )

        elif mode == "codigo":
            answer = (
                "Analise tecnica simulada do MockProvider:\n\n"
                "```python\n"
                "def exemplo():\n"
                "    return 'PedroCore IA funcionando'\n"
                "```\n\n"
                "Esse retorno e mockado para testar a interface e o fluxo da API."
            )

        elif mode == "tecnico":
            answer = (
                "Resposta tecnica simulada do MockProvider.\n\n"
                "A V2 possui arquitetura multi-provider para Mock, Gemini, OpenAI, "
                "Claude, DeepSeek e Grok.\n"
                "Quando uma chave real estiver configurada, o provider selecionado "
                "podera responder de verdade.\n\n"
                f"Modelo solicitado: {selected_model}\n"
                f"Mensagem recebida: {message}"
            )

        else:
            answer = (
                "Ola, eu sou o PedroCore IA. "
                "Recebi sua mensagem e estou funcionando em modo de teste."
            )

        return SimpleNamespace(
            answer=answer,
            provider=self.name,
            model=selected_model,
        )
