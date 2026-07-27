"""Observabilidade do orçamento de saída, sem conteúdo sensível.

Confirma que os novos metadados aparecem na projeção local e que nada de
sensível — prompt, contexto financeiro, credencial — entra junto com eles.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.observability.service import FLAG_ENABLED, observability_service
from app.modules.output_budget.service import output_budget_service
from app.modules.provider_health.service import (
    FLAG_CIRCUIT_ENABLED,
    provider_health_service,
)
from app.modules.providers.base import ProviderResponse, ProviderTransportTimeoutError
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.shadow_routing.schemas import RoutingMode
from app.modules.shadow_routing.service import FLAG_ROUTING_MODE

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FINGUARD_KEY = "finguard-observability-budget"
FAKE_PROVIDER_KEY = "observability-synthetic-never-real"

SECRET_LOOKING_KEY = "AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMYDUMMY1234"
PROMPT_MARKER = "MARCADOR_DE_PROMPT_QUE_NAO_PODE_VAZAR"

REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-observability",
            "api_key": FINGUARD_KEY,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
        }
    ]
)


@pytest.fixture(autouse=True)
def reset_state():
    provider_health_service.reset()
    observability_service.reset()
    yield
    provider_health_service.reset()
    observability_service.reset()


@pytest.fixture
def observable(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, REGISTRY)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    monkeypatch.delenv(FLAG_CIRCUIT_ENABLED, raising=False)
    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)


def _install(monkeypatch, outcome=None):
    async def fake(
        self_provider,
        message,
        mode,
        model,
        system_prompt=None,
        output_budget=None,
        transport_timeout_ms=None,
    ):
        del self_provider, message, mode, system_prompt
        if isinstance(outcome, BaseException):
            raise outcome
        return ProviderResponse(
            answer="Resposta sintética observável.",
            provider="gemini",
            model=model,
            finish_reason="STOP",
            input_tokens=7,
            output_tokens=13,
            total_tokens=20,
            output_budget=output_budget,
            transport_timeout_ms=transport_timeout_ms,
        )

    monkeypatch.setattr(GeminiProvider, "generate_response", fake)


def _post(**overrides):
    payload = {
        "message": f"pergunta com {PROMPT_MARKER}",
        "provider": "auto",
        "task_type": "assistant_chat",
        "origin_system": "finguard",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    return client.post(
        "/api/orchestrate", json=payload, headers={AUTH_HEADER: FINGUARD_KEY}
    )


def _last_record():
    summaries = observability_service.list()
    assert summaries, "Nenhuma execução registrada."
    record = observability_service.get(summaries[0].execution_id)
    assert record is not None
    return record


# ------------------------------------------------------- campos registrados


def test_generation_budget_projection_carries_budget_and_times(
    observable, monkeypatch
):
    _install(monkeypatch)

    _post()
    budget = _last_record().generation_budget

    assert budget["effective_budget"] == output_budget_service.task_cap(
        "assistant_chat"
    )
    assert budget["global_cap"] == output_budget_service.global_cap()
    assert budget["model_cap"] == 8192
    assert budget["budget_source"] == "task_cap"
    assert budget["budget_clamped"] is True
    assert budget["transport_timeout_ms"] < budget["orchestration_timeout_ms"]


def test_projection_carries_finish_reason_and_tokens(observable, monkeypatch):
    _install(monkeypatch)

    _post()
    budget = _last_record().generation_budget

    assert budget["finish_reason"] == "STOP"
    assert budget["input_tokens"] == 7
    assert budget["output_tokens"] == 13
    assert budget["total_tokens"] == 20
    assert budget["output_truncated"] is False


def test_provider_attempt_carries_the_new_structured_fields(observable, monkeypatch):
    _install(monkeypatch)

    _post()
    attempt = _last_record().provider_attempts[0].model_dump()

    assert attempt["output_budget"] == output_budget_service.task_cap("assistant_chat")
    assert attempt["budget_source"] == "task_cap"
    assert attempt["finish_reason"] == "STOP"
    assert attempt["output_truncated"] is False
    assert attempt["completion_certainty"] == "completed"


def test_transport_cancellation_is_visible_next_to_the_ambiguity(
    observable, monkeypatch
):
    _install(monkeypatch, ProviderTransportTimeoutError("transporte expirou"))

    _post()
    record = _last_record()
    budget = record.generation_budget
    attempt = record.provider_attempts[0].model_dump()

    assert budget["transport_cancelled_locally"] is True
    assert attempt["completion_certainty"] == "ambiguous"


def test_absent_metrics_stay_absent_instead_of_being_invented(
    observable, monkeypatch
):
    async def fake(
        self_provider,
        message,
        mode,
        model,
        system_prompt=None,
        output_budget=None,
        transport_timeout_ms=None,
    ):
        del self_provider, message, mode, system_prompt
        del output_budget, transport_timeout_ms
        return ProviderResponse(answer="sem métricas", provider="gemini", model=model)

    monkeypatch.setattr(GeminiProvider, "generate_response", fake)

    _post()
    budget = _last_record().generation_budget

    assert budget["input_tokens"] is None
    assert budget["output_tokens"] is None
    assert budget["total_tokens"] is None
    assert budget["finish_reason"] is None


def test_retry_stays_constant_because_retry_does_not_exist(observable, monkeypatch):
    _install(monkeypatch)

    _post()

    assert _last_record().retry == {"attempted": False, "count": 0}


def test_mock_path_produces_no_budget_projection(observable, monkeypatch):
    _post(allow_real_provider=False)

    assert _last_record().generation_budget is None


# --------------------------------------------------------- nada de sensível


def _serialized_budget_and_attempts() -> str:
    record = _last_record()
    payload = {
        "generation_budget": record.generation_budget,
        "provider_attempts": [item.model_dump() for item in record.provider_attempts],
    }
    return json.dumps(payload, default=str)


def test_budget_metadata_contains_no_prompt(observable, monkeypatch):
    _install(monkeypatch)

    _post()

    assert PROMPT_MARKER not in _serialized_budget_and_attempts()


def test_budget_metadata_contains_no_financial_context(observable, monkeypatch):
    _install(monkeypatch)

    _post(context={"financial_context": {"saldo": 1234.56, "divida": 9876.54}})

    serialized = _serialized_budget_and_attempts()
    assert "1234.56" not in serialized
    assert "9876.54" not in serialized


def test_financial_context_stays_omitted_in_the_sanitized_payload(
    observable, monkeypatch
):
    _install(monkeypatch)

    _post(context={"financial_context": {"saldo": 1234.56}})
    record = _last_record()

    financial = record.payload_sanitized["context"]["financial_context"]
    assert financial["omitted"] is True
    assert "1234.56" not in json.dumps(record.payload_sanitized, default=str)


def test_no_credential_reaches_the_observability_record(observable, monkeypatch):
    _install(monkeypatch)

    _post()
    serialized = json.dumps(_last_record().model_dump(), default=str)

    assert FINGUARD_KEY not in serialized
    assert FAKE_PROVIDER_KEY not in serialized


def test_secret_looking_values_are_redacted(observable, monkeypatch):
    _install(monkeypatch)

    _post(message=f"minha chave é {SECRET_LOOKING_KEY}")
    serialized = json.dumps(_last_record().model_dump(), default=str)

    assert SECRET_LOOKING_KEY not in serialized
    assert "[REDACTED_KEY]" in serialized


def test_system_prompt_is_redacted(observable, monkeypatch):
    _install(monkeypatch)

    _post(system_prompt=f"instrução secreta {PROMPT_MARKER}")
    record = _last_record()

    assert record.payload_sanitized["system_prompt"] == "[REDACTED]"
