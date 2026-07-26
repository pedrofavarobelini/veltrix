from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResponse:
    answer: str
    provider: str
    model: str


class ProviderConfigError(Exception):
    """Erro de configuração de provider, como chave ausente."""


class ProviderExecutionError(Exception):
    """Erro de execução da API do provider."""


class BaseAIProvider(ABC):
    name: str
    label: str
    default_model: str
    real_provider: bool = True

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    async def generate_response(
        self,
        message: str,
        mode: str,
        model: str,
        system_prompt: str | None = None,
    ) -> ProviderResponse:
        pass

    def build_prompt(
        self,
        message: str,
        mode: str,
        system_prompt: str | None = None,
    ) -> str:
        base_prompt = system_prompt or (
            "Você é o PedroCore IA, um assistente pessoal técnico, claro, direto e útil."
        )

        mode_instruction = {
            "normal": "Responda de forma natural, clara e útil.",
            "tecnico": "Responda de forma técnica, organizada, objetiva e sem enrolação.",
            "resumido": "Responda de forma curta, direta e prática.",
            "codigo": "Priorize explicação técnica, exemplos de código e passos de implementação.",
        }.get(mode, "Responda de forma clara e útil.")

        return f"""
{base_prompt}

Modo de resposta:
{mode_instruction}

Mensagem do usuário:
{message}
""".strip()
