"""Adapter Gemini assíncrono com orçamento e timeout de transporte.

Somente fakes: o cliente é substituído, mas `GenerateContentConfig` e
`HttpOptions` são os tipos REAIS do `google-genai` instalado. Nenhuma chamada
de rede, nenhuma credencial real.
"""

from __future__ import annotations

import ast
import asyncio
import inspect

import pytest
from google.genai import types as real_genai_types

from app.core.config import settings
from app.modules.providers import gemini_provider as adapter_module
from app.modules.providers.base import (
    ProviderConfigError,
    ProviderExecutionError,
    ProviderOutputRejectedError,
    ProviderTransportTimeoutError,
)
from app.modules.providers.gemini_provider import GeminiProvider
from tests.gemini_fakes import install_fake_sdk, never_finishes, response, usage

BUDGET = 4096
TIMEOUT_MS = 27_000

# Capturado no import, ANTES de o guard global do conftest substituir o método.
# É o adapter de verdade que queremos exercitar — contra um SDK falso.
_REAL_GENERATE_RESPONSE = GeminiProvider.generate_response


@pytest.fixture(autouse=True)
def configured_key(monkeypatch):
    # Chave sintética: o cliente real nunca é construído neste arquivo.
    monkeypatch.setattr(settings, "gemini_api_key", "chave-sintetica-de-teste")


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(
        GeminiProvider, "generate_response", _REAL_GENERATE_RESPONSE
    )
    return GeminiProvider()


async def _generate(provider, **overrides):
    kwargs = {
        "message": "pergunta sintética",
        "mode": "tecnico",
        "model": "gemini-3.5-flash",
        "system_prompt": "prompt sintético",
        "output_budget": BUDGET,
        "transport_timeout_ms": TIMEOUT_MS,
    }
    kwargs.update(overrides)
    return await provider.generate_response(**kwargs)


# ------------------------------------------------- configuração de geração


def test_generation_config_carries_the_effective_output_budget(provider, monkeypatch):
    fake = install_fake_sdk(monkeypatch)

    asyncio.run(_generate(provider))

    config = fake.client.calls[0]["config"]
    assert isinstance(config, real_genai_types.GenerateContentConfig)
    assert config.max_output_tokens == BUDGET


def test_http_options_carry_the_transport_timeout_in_milliseconds(
    provider, monkeypatch
):
    fake = install_fake_sdk(monkeypatch)

    asyncio.run(_generate(provider))

    http_options = fake.client.http_options
    assert isinstance(http_options, real_genai_types.HttpOptions)
    assert http_options.timeout == TIMEOUT_MS
    # Milissegundos, não segundos: 27000 e não 27.
    assert http_options.timeout > 1_000


def test_no_retry_options_are_configured(provider, monkeypatch):
    fake = install_fake_sdk(monkeypatch)

    asyncio.run(_generate(provider))

    assert fake.client.http_options.retry_options is None


def test_exactly_one_generate_content_call_per_logical_request(provider, monkeypatch):
    fake = install_fake_sdk(monkeypatch)

    asyncio.run(_generate(provider))

    assert len(fake.instances) == 1
    assert len(fake.client.calls) == 1


def test_adapter_refuses_to_run_without_a_budget(provider, monkeypatch):
    install_fake_sdk(monkeypatch)

    with pytest.raises(ProviderExecutionError):
        asyncio.run(_generate(provider, output_budget=None))


@pytest.mark.parametrize("invalid", [0, -1, "4096", 4096.0, True])
def test_adapter_refuses_invalid_budget(provider, monkeypatch, invalid):
    install_fake_sdk(monkeypatch)

    with pytest.raises(ProviderExecutionError):
        asyncio.run(_generate(provider, output_budget=invalid))


@pytest.mark.parametrize("invalid", [None, 0, -1, "27000", 27_000.0, True])
def test_adapter_refuses_invalid_transport_timeout(provider, monkeypatch, invalid):
    install_fake_sdk(monkeypatch)

    with pytest.raises(ProviderExecutionError):
        asyncio.run(_generate(provider, transport_timeout_ms=invalid))


def test_missing_credential_is_rejected_before_touching_the_sdk(provider, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    fake = install_fake_sdk(monkeypatch)

    with pytest.raises(ProviderConfigError):
        asyncio.run(_generate(provider))

    assert fake.instances == []


# --------------------------------------------------------- cliente assíncrono


def test_adapter_uses_the_native_async_client(provider, monkeypatch):
    fake = install_fake_sdk(monkeypatch)

    asyncio.run(_generate(provider))

    # A chamada foi registrada pelo caminho `client.aio.models`.
    assert fake.client.calls
    assert inspect.iscoroutinefunction(GeminiProvider.generate_response)


def test_adapter_code_no_longer_calls_to_thread():
    # AST, não busca textual: o docstring do módulo cita `asyncio.to_thread`
    # justamente para explicar o que foi removido.
    tree = ast.parse(inspect.getsource(adapter_module))
    attributes = {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }

    assert "to_thread" not in attributes
    assert "run_in_executor" not in attributes
    assert "generate_content" in attributes


def test_client_is_closed_on_success(provider, monkeypatch):
    fake = install_fake_sdk(monkeypatch)

    asyncio.run(_generate(provider))

    assert fake.client.closed == 1


def test_client_is_closed_on_provider_error(provider, monkeypatch):
    fake = install_fake_sdk(monkeypatch, RuntimeError("erro sintético do SDK"))

    with pytest.raises(ProviderExecutionError):
        asyncio.run(_generate(provider))

    assert fake.client.closed == 1


def test_client_is_closed_on_transport_timeout(provider, monkeypatch):
    fake = install_fake_sdk(monkeypatch, TimeoutError("transporte sintético expirou"))

    with pytest.raises(ProviderTransportTimeoutError):
        asyncio.run(_generate(provider))

    assert fake.client.closed == 1


def test_client_is_closed_on_task_cancellation(provider, monkeypatch):
    fake = install_fake_sdk(monkeypatch, never_finishes)

    async def scenario():
        task = asyncio.create_task(_generate(provider))
        await asyncio.sleep(0)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(task, timeout=0.05)

    asyncio.run(scenario())

    assert fake.client.closed == 1


def test_close_failure_never_masks_the_original_result(provider, monkeypatch):
    fake = install_fake_sdk(monkeypatch, broken_close=True)

    result = asyncio.run(_generate(provider))

    assert result.answer
    assert fake.client.closed == 1


def test_close_failure_never_masks_the_original_error(provider, monkeypatch):
    install_fake_sdk(
        monkeypatch, RuntimeError("erro sintético do SDK"), broken_close=True
    )

    with pytest.raises(ProviderExecutionError) as excinfo:
        asyncio.run(_generate(provider))

    assert "fechar" not in str(excinfo.value)


# ------------------------------------------------------------- normalização


def test_normal_response_carries_budget_timeout_and_finish_reason(
    provider, monkeypatch
):
    install_fake_sdk(
        monkeypatch,
        response(text="tudo certo", finish_reason="STOP", usage_metadata=usage(11, 22, 33)),
    )

    result = asyncio.run(_generate(provider))

    assert result.answer == "tudo certo"
    assert result.finish_reason == "STOP"
    assert result.truncated is False
    assert result.output_budget == BUDGET
    assert result.transport_timeout_ms == TIMEOUT_MS
    assert (result.input_tokens, result.output_tokens, result.total_tokens) == (11, 22, 33)


def test_empty_text_is_rejected(provider, monkeypatch):
    install_fake_sdk(monkeypatch, response(text="   ", finish_reason="STOP"))

    with pytest.raises(ProviderExecutionError):
        asyncio.run(_generate(provider))


def test_absent_finish_reason_with_usable_text_is_accepted(provider, monkeypatch):
    install_fake_sdk(monkeypatch, response(text="resposta", finish_reason=None))

    result = asyncio.run(_generate(provider))

    assert result.finish_reason is None
    assert result.truncated is False


def test_missing_usage_metadata_never_fails_and_never_estimates(provider, monkeypatch):
    install_fake_sdk(monkeypatch, response(text="resposta", usage_metadata=None))

    result = asyncio.run(_generate(provider))

    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.total_tokens is None


@pytest.mark.parametrize("bad", [-1, "12", 3.5, True])
def test_invalid_token_counts_are_dropped_not_accepted(provider, monkeypatch, bad):
    install_fake_sdk(
        monkeypatch, response(usage_metadata=usage(bad, bad, bad))
    )

    result = asyncio.run(_generate(provider))

    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.total_tokens is None


def test_total_below_the_sum_is_dropped_as_inconsistent(provider, monkeypatch):
    install_fake_sdk(monkeypatch, response(usage_metadata=usage(100, 100, 50)))

    result = asyncio.run(_generate(provider))

    assert result.input_tokens == 100
    assert result.output_tokens == 100
    assert result.total_tokens is None


def test_total_above_the_sum_is_kept_because_of_thinking_tokens(provider, monkeypatch):
    install_fake_sdk(monkeypatch, response(usage_metadata=usage(10, 20, 90)))

    result = asyncio.run(_generate(provider))

    assert result.total_tokens == 90


# --------------------------------------------------------------- truncamento


def test_max_tokens_is_detected_as_truncation(provider, monkeypatch):
    install_fake_sdk(
        monkeypatch,
        response(text="resposta cortada pela met", finish_reason="MAX_TOKENS"),
    )

    with pytest.raises(ProviderOutputRejectedError) as excinfo:
        asyncio.run(_generate(provider))

    assert excinfo.value.truncated is True
    assert excinfo.value.finish_reason == "MAX_TOKENS"


def test_truncated_partial_text_is_never_returned_as_an_answer(provider, monkeypatch):
    partial = "conteúdo parcial que não pode virar resposta"
    install_fake_sdk(monkeypatch, response(text=partial, finish_reason="MAX_TOKENS"))

    with pytest.raises(ProviderOutputRejectedError) as excinfo:
        asyncio.run(_generate(provider))

    assert partial not in str(excinfo.value)


def test_truncation_triggers_exactly_one_call_and_no_continuation(
    provider, monkeypatch
):
    fake = install_fake_sdk(monkeypatch, response(finish_reason="MAX_TOKENS"))

    with pytest.raises(ProviderOutputRejectedError):
        asyncio.run(_generate(provider))

    assert len(fake.client.calls) == 1
    assert len(fake.instances) == 1


@pytest.mark.parametrize(
    "finish_reason",
    [
        "SAFETY",
        "RECITATION",
        "MALFORMED_FUNCTION_CALL",
        "OTHER",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
        "LANGUAGE",
        "UNEXPECTED_TOOL_CALL",
    ],
)
def test_abnormal_finish_reasons_are_treated_conservatively(
    provider, monkeypatch, finish_reason
):
    install_fake_sdk(
        monkeypatch, response(text="conteúdo", finish_reason=finish_reason)
    )

    with pytest.raises(ProviderOutputRejectedError) as excinfo:
        asyncio.run(_generate(provider))

    assert excinfo.value.truncated is False
    assert excinfo.value.finish_reason == finish_reason
    # A mensagem técnica carrega só o rótulo, nunca o conteúdo gerado.
    assert "conteúdo" not in str(excinfo.value)


def test_finish_reason_unspecified_is_treated_as_normal(provider, monkeypatch):
    install_fake_sdk(
        monkeypatch,
        response(text="resposta", finish_reason="FINISH_REASON_UNSPECIFIED"),
    )

    result = asyncio.run(_generate(provider))

    assert result.answer == "resposta"


def test_truncation_is_never_inferred_from_response_length(provider, monkeypatch):
    # Texto longo com STOP não é truncamento: só `finish_reason` decide.
    install_fake_sdk(
        monkeypatch, response(text="x" * 50_000, finish_reason="STOP")
    )

    result = asyncio.run(_generate(provider))

    assert result.truncated is False


# ------------------------------------------------------ timeout de transporte


def test_httpx_timeout_becomes_a_transport_timeout_error(provider, monkeypatch):
    import httpx

    install_fake_sdk(monkeypatch, httpx.ReadTimeout("transporte sintético"))

    with pytest.raises(ProviderTransportTimeoutError):
        asyncio.run(_generate(provider))


def test_generic_sdk_failure_is_not_reported_as_transport_timeout(
    provider, monkeypatch
):
    install_fake_sdk(monkeypatch, ValueError("erro genérico do SDK"))

    with pytest.raises(ProviderExecutionError) as excinfo:
        asyncio.run(_generate(provider))

    assert not isinstance(excinfo.value, ProviderTransportTimeoutError)


def test_cancellation_propagates_and_is_not_swallowed(provider, monkeypatch):
    install_fake_sdk(monkeypatch, never_finishes)

    async def scenario():
        task = asyncio.create_task(_generate(provider))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
