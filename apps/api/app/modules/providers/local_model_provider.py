import os
from abc import ABC, abstractmethod

from app.modules.providers.base import (
    BaseAIProvider,
    ProviderConfigError,
    ProviderExecutionError,
    ProviderResponse,
)
from app.modules.providers.local_model_contract import SUPPORTED_BACKENDS

# Local Model Provider opt-in (PEDROCORE-LOCAL-MODEL-01).
#
# Provider GENERATIVO local, distinto do local_qa (determinístico de QA):
#   - default OFF (PEDROCORE_ENABLE_LOCAL_MODEL=false);
#   - nunca usa chave externa; real_provider=False;
#   - nunca entra em RELEASE_GATE_TRUSTED_PROVIDERS;
#   - NENHUMA chamada de rede nesta frente: o transport padrão é None e a
#     chamada real fica para quando o operador instalar um backend local
#     (Ollama/llama.cpp/LM Studio/compatível OpenAI local) e um transport
#     real for implementado em frente própria. Testes usam fake transport.

FLAG_ENABLE_LOCAL_MODEL = "PEDROCORE_ENABLE_LOCAL_MODEL"
FLAG_LOCAL_MODEL_BACKEND = "PEDROCORE_LOCAL_MODEL_BACKEND"
FLAG_LOCAL_MODEL_ENDPOINT = "PEDROCORE_LOCAL_MODEL_ENDPOINT"
FLAG_LOCAL_MODEL_NAME = "PEDROCORE_LOCAL_MODEL_NAME"
FLAG_LOCAL_MODEL_TIMEOUT = "PEDROCORE_LOCAL_MODEL_TIMEOUT_SECONDS"

DISABLED_BACKEND = "disabled"

# Backends aceitos em runtime: os do contrato + adapter OpenAI-compatible local.
SUPPORTED_RUNTIME_BACKENDS = SUPPORTED_BACKENDS | {"openai_compatible_local"}

MAX_ANSWER_CHARS = 20_000


def local_model_enabled() -> bool:
    raw = (os.environ.get(FLAG_ENABLE_LOCAL_MODEL) or "").strip().lower()
    return raw == "true"


def local_model_backend() -> str:
    return (os.environ.get(FLAG_LOCAL_MODEL_BACKEND) or DISABLED_BACKEND).strip().lower()


def local_model_endpoint() -> str:
    return (os.environ.get(FLAG_LOCAL_MODEL_ENDPOINT) or "").strip()


def local_model_name() -> str:
    return (os.environ.get(FLAG_LOCAL_MODEL_NAME) or "local-model").strip()


def local_model_timeout_seconds() -> float:
    raw = (os.environ.get(FLAG_LOCAL_MODEL_TIMEOUT) or "30").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 30.0


def local_model_ready() -> bool:
    """Habilitado por flag E backend válido configurado."""
    backend = local_model_backend()
    return (
        local_model_enabled()
        and backend != DISABLED_BACKEND
        and backend in SUPPORTED_RUNTIME_BACKENDS
    )


class LocalModelTransport(ABC):
    """Interface de transporte para o backend local; testável por fake."""

    @abstractmethod
    async def generate(
        self,
        *,
        endpoint: str,
        model: str,
        prompt: str,
        timeout_seconds: float,
    ) -> str:
        pass


class LocalModelProvider(BaseAIProvider):
    name = "local_model"
    label = "Local Model (generativo local, opt-in)"
    default_model = "local-model"
    real_provider = False

    def __init__(self) -> None:
        # Sem transport padrão: nenhuma chamada de rede acontece nesta frente.
        self._transport: LocalModelTransport | None = None

    def set_transport(self, transport: LocalModelTransport | None) -> None:
        self._transport = transport

    @property
    def is_configured(self) -> bool:
        return local_model_ready()

    async def generate_response(
        self,
        message: str,
        mode: str,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> ProviderResponse:
        if not local_model_ready():
            raise ProviderConfigError(
                "Local model desabilitado: exige PEDROCORE_ENABLE_LOCAL_MODEL=true "
                "e PEDROCORE_LOCAL_MODEL_BACKEND válido."
            )
        if self._transport is None:
            raise ProviderExecutionError(
                "Nenhum transport local disponível: a chamada real ao backend "
                "local não está implementada nesta frente; instale/implante o "
                "backend e o transport em frente própria."
            )

        selected_model = model or local_model_name()
        prompt = self.build_prompt(message=message, mode=mode, system_prompt=system_prompt)
        answer = await self._transport.generate(
            endpoint=local_model_endpoint(),
            model=selected_model,
            prompt=prompt,
            timeout_seconds=local_model_timeout_seconds(),
        )
        answer = (answer or "").strip()
        if not answer:
            raise ProviderExecutionError("Backend local retornou resposta vazia.")

        return ProviderResponse(
            answer=answer[:MAX_ANSWER_CHARS],
            provider=self.name,
            model=selected_model,
        )


local_model_provider = LocalModelProvider()
