"""Fakes determinísticos do SDK Gemini (OUTPUT-BUDGET-CANCELLATION-01).

Nenhuma chamada de rede, nenhuma credencial real. Apenas o *cliente* é falso:
`GenerateContentConfig` e `HttpOptions` continuam sendo os tipos REAIS do
`google-genai` instalado, para que as asserções sobre orçamento de saída e
timeout de transporte valham contra o SDK de verdade, não contra um dublê.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from google.genai import types as real_genai_types


class FakeUsageMetadata(SimpleNamespace):
    """Espelha os nomes usados por `GenerateContentResponseUsageMetadata`."""


def usage(
    prompt_token_count: Any = None,
    candidates_token_count: Any = None,
    total_token_count: Any = None,
) -> FakeUsageMetadata:
    return FakeUsageMetadata(
        prompt_token_count=prompt_token_count,
        candidates_token_count=candidates_token_count,
        total_token_count=total_token_count,
    )


def response(
    text: str = "Resposta sintética do fake.",
    finish_reason: str | None = "STOP",
    usage_metadata: Any = None,
) -> SimpleNamespace:
    candidates = (
        [SimpleNamespace(finish_reason=finish_reason)]
        if finish_reason is not None
        else []
    )
    return SimpleNamespace(
        text=text,
        candidates=candidates,
        usage_metadata=usage_metadata,
    )


class FakeAsyncModels:
    def __init__(self, client: "FakeClient") -> None:
        self._client = client

    async def generate_content(self, *, model, contents, config):
        self._client.calls.append(
            {"model": model, "contents": contents, "config": config}
        )
        behavior = self._client.behavior
        if callable(behavior):
            return await behavior(self._client)
        if isinstance(behavior, BaseException):
            raise behavior
        return behavior


class FakeAsyncClient:
    def __init__(self, client: "FakeClient") -> None:
        self._client = client
        self.models = FakeAsyncModels(client)

    async def aclose(self) -> None:
        self._client.closed += 1
        if self._client.broken_close:
            raise RuntimeError("falha sintética ao fechar o cliente")


class FakeClient:
    """Cliente falso com a mesma superfície que o adapter realmente usa."""

    def __init__(self, *, api_key=None, http_options=None, **_: Any) -> None:
        self.api_key = api_key
        self.http_options = http_options
        self.calls: list[dict[str, Any]] = []
        self.closed = 0
        self.broken_close = False
        self.behavior: Any = response()
        self.aio = FakeAsyncClient(self)


class FakeGenaiModule:
    """Substitui apenas `google.genai`; os tipos continuam sendo os reais."""

    def __init__(self, behavior: Any = None, broken_close: bool = False) -> None:
        self.instances: list[FakeClient] = []
        self.behavior = behavior if behavior is not None else response()
        self.broken_close = broken_close

    def Client(self, **kwargs: Any) -> FakeClient:  # noqa: N802 - espelha o SDK
        client = FakeClient(**kwargs)
        client.behavior = self.behavior
        client.broken_close = self.broken_close
        self.instances.append(client)
        return client

    @property
    def client(self) -> FakeClient:
        assert self.instances, "Nenhum cliente Gemini foi construído."
        return self.instances[-1]


def install_fake_sdk(
    monkeypatch, behavior: Any = None, broken_close: bool = False
) -> FakeGenaiModule:
    """Injeta o fake no ponto de import tardio do adapter."""
    from app.modules.providers import gemini_provider as adapter_module

    fake = FakeGenaiModule(behavior, broken_close=broken_close)
    monkeypatch.setattr(
        adapter_module,
        "_load_genai",
        lambda: (fake, real_genai_types),
    )
    return fake


async def never_finishes(_client: FakeClient) -> None:
    """Geração que nunca termina sozinha, para exercitar cancelamento."""
    await asyncio.sleep(3600)
