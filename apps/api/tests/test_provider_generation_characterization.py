"""Caracterização do orçamento e do tempo do provider Gemini.

Este arquivo fixa invariantes que valem ANTES e DEPOIS da frente
OUTPUT-BUDGET-CANCELLATION-01, para que a migração não as quebre em silêncio:

  - o consumidor nunca envia orçamento, tokens ou timeout;
  - não existe retry em nenhuma camada — nem no adapter, nem na orquestração,
    nem no SDK instalado;
  - o SDK instalado realmente possui as capacidades que a frente vai usar.

Nenhuma chamada de rede e nenhuma credencial real.
"""

from __future__ import annotations

import ast
import inspect

from google import genai
from google.genai import _api_client, types as genai_types

from app.modules.chat.schemas import ChatRequest
from app.modules.orchestration import service as orchestration_module
from app.modules.providers import gemini_provider as adapter_module


# ------------------------------------- o consumidor não controla a geração


def test_consumer_contract_has_no_generation_control_field():
    fields = set(ChatRequest.model_fields)

    assert "max_output_tokens" not in fields
    assert "max_tokens" not in fields
    assert "output_budget" not in fields
    assert "timeout" not in fields
    assert "transport_timeout_ms" not in fields


def test_consumer_contract_still_exposes_only_the_known_opt_ins():
    fields = set(ChatRequest.model_fields)

    assert {"allow_real_provider", "allow_local_model", "context_from_memory"} <= fields


# ---------------------------------------------------- ausência de retry


def test_orchestration_has_no_retry_loop_around_the_provider():
    source = inspect.getsource(orchestration_module)

    assert "for attempt in range" not in source
    assert "while True" not in source


def test_adapter_never_calls_the_provider_inside_a_loop():
    # Iterar sobre `candidates` é normalização, não repetição de chamada.
    # O que não pode existir é despacho externo dentro de laço.
    tree = ast.parse(inspect.getsource(adapter_module))

    def dispatches(node) -> bool:
        return any(
            isinstance(inner, ast.Attribute) and inner.attr == "generate_content"
            for inner in ast.walk(node)
        )

    loops = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.For, ast.While, ast.AsyncFor))
    ]

    assert [loop for loop in loops if dispatches(loop)] == []


def test_installed_sdk_does_not_retry_by_default():
    # `retry_args(None)` é o caminho usado quando ninguém passa
    # `HttpRetryOptions`: uma tentativa, sem repetição.
    args = _api_client.retry_args(None)

    assert args["stop"].max_attempt_number == 1


def test_http_options_default_has_no_retry_options():
    assert genai_types.HttpOptions().retry_options is None


# ------------------------------ capacidades reais do SDK instalado (2.9.0)


def test_installed_sdk_is_the_current_google_gen_ai_sdk():
    assert genai.__version__.startswith("2.")


def test_sdk_supports_an_explicit_output_budget():
    config = genai_types.GenerateContentConfig(max_output_tokens=4096)

    assert config.max_output_tokens == 4096


def test_sdk_supports_an_explicit_transport_timeout_in_milliseconds():
    options = genai_types.HttpOptions(timeout=27_000)

    assert options.timeout == 27_000


def test_sdk_exposes_a_native_async_client_with_explicit_close():
    assert hasattr(genai.Client, "aio")
    assert inspect.iscoroutinefunction(
        genai.client.AsyncClient.aclose  # type: ignore[attr-defined]
    )


def test_sdk_reports_truncation_through_finish_reason():
    assert genai_types.FinishReason.MAX_TOKENS.value == "MAX_TOKENS"
    assert genai_types.FinishReason.STOP.value == "STOP"


def test_sdk_reports_token_usage_field_names_used_by_the_adapter():
    fields = set(genai_types.GenerateContentResponseUsageMetadata.model_fields)

    assert {
        "prompt_token_count",
        "candidates_token_count",
        "total_token_count",
    } <= fields
