"""Correções residuais (FINGUARD-PEDROCORE-ASSISTANT-FINAL-CLOSE-01).

Dois defeitos confirmados na auditoria da frente de output budget:

1. a auditoria registrava fechamento de transporte como concluído a partir de
   uma flag de capacidade da classe, mesmo quando `aclose()` falhava — ou
   quando o resultado sequer era observável (timeout da orquestração);
2. `finish_reason` anormal e `MAX_TOKENS` descartavam `usage_metadata`,
   orçamento e timeout, justamente nos casos em que o custo já foi incorrido.

Tentativa de fechamento nunca é fechamento confirmado.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.output_budget.service import output_budget_service
from app.modules.provider_health.service import (
    FLAG_CIRCUIT_ENABLED,
    provider_health_service,
)
from app.modules.providers.base import (
    ProviderOutputRejectedError,
    ProviderResponse,
    ProviderTransportTimeoutError,
    TransportClose,
)
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.shadow_routing.schemas import RoutingMode
from app.modules.shadow_routing.service import FLAG_ROUTING_MODE
from tests.gemini_fakes import install_fake_sdk, never_finishes, response, usage

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FINGUARD_KEY = "finguard-final-close-registered"
FAKE_PROVIDER_KEY = "final-close-synthetic-never-real"
BUDGET = 4096
TIMEOUT_MS = 27_000

_REAL_GENERATE_RESPONSE = GeminiProvider.generate_response

REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-final-close",
            "api_key": FINGUARD_KEY,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
        }
    ]
)


@pytest.fixture(autouse=True)
def reset_circuits():
    provider_health_service.reset()
    yield
    provider_health_service.reset()


# =====================================================================
# 1. Semântica de fechamento do transporte — nível do adapter
# =====================================================================


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "chave-sintetica-de-teste")
    monkeypatch.setattr(GeminiProvider, "generate_response", _REAL_GENERATE_RESPONSE)
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


def test_successful_close_is_reported_as_confirmed(adapter, monkeypatch):
    install_fake_sdk(monkeypatch)

    result = asyncio.run(_generate(adapter))

    assert result.transport_close is TransportClose.CONFIRMED


def test_failed_close_is_reported_as_failed_not_confirmed(adapter, monkeypatch):
    fake = install_fake_sdk(monkeypatch, broken_close=True)

    result = asyncio.run(_generate(adapter))

    # O fechamento foi TENTADO e FALHOU. Nunca pode virar "confirmado".
    assert result.transport_close is TransportClose.FAILED
    assert fake.client.closed == 1


def test_failed_close_still_does_not_mask_the_answer(adapter, monkeypatch):
    install_fake_sdk(monkeypatch, broken_close=True)

    result = asyncio.run(_generate(adapter))

    assert result.answer


def test_transport_timeout_reports_the_real_close_outcome(adapter, monkeypatch):
    install_fake_sdk(
        monkeypatch, TimeoutError("transporte sintético expirou"), broken_close=True
    )

    with pytest.raises(ProviderTransportTimeoutError) as excinfo:
        asyncio.run(_generate(adapter))

    assert excinfo.value.transport_close is TransportClose.FAILED


def test_transport_timeout_with_healthy_close_is_confirmed(adapter, monkeypatch):
    install_fake_sdk(monkeypatch, TimeoutError("transporte sintético expirou"))

    with pytest.raises(ProviderTransportTimeoutError) as excinfo:
        asyncio.run(_generate(adapter))

    assert excinfo.value.transport_close is TransportClose.CONFIRMED


def test_client_is_closed_exactly_once(adapter, monkeypatch):
    fake = install_fake_sdk(monkeypatch)

    asyncio.run(_generate(adapter))

    assert fake.client.closed == 1


def test_cancellation_still_closes_the_client(adapter, monkeypatch):
    fake = install_fake_sdk(monkeypatch, never_finishes)

    async def scenario():
        task = asyncio.create_task(_generate(adapter))
        await asyncio.sleep(0)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(task, timeout=0.05)

    asyncio.run(scenario())

    assert fake.client.closed == 1


# =====================================================================
# 2. Metadados preservados em truncamento e finish_reason anormal
# =====================================================================


def test_truncation_preserves_usage_metadata(adapter, monkeypatch):
    install_fake_sdk(
        monkeypatch,
        response(
            text="cortado", finish_reason="MAX_TOKENS", usage_metadata=usage(31, 41, 72)
        ),
    )

    with pytest.raises(ProviderOutputRejectedError) as excinfo:
        asyncio.run(_generate(adapter))

    error = excinfo.value
    assert error.truncated is True
    assert (error.input_tokens, error.output_tokens, error.total_tokens) == (31, 41, 72)
    assert error.output_budget == BUDGET
    assert error.transport_timeout_ms == TIMEOUT_MS


def test_abnormal_finish_reason_preserves_usage_metadata(adapter, monkeypatch):
    install_fake_sdk(
        monkeypatch,
        response(
            text="bloqueado", finish_reason="SAFETY", usage_metadata=usage(5, 6, 11)
        ),
    )

    with pytest.raises(ProviderOutputRejectedError) as excinfo:
        asyncio.run(_generate(adapter))

    error = excinfo.value
    assert error.truncated is False
    assert (error.input_tokens, error.output_tokens, error.total_tokens) == (5, 6, 11)


def test_truncation_without_usage_metadata_keeps_none(adapter, monkeypatch):
    install_fake_sdk(
        monkeypatch, response(finish_reason="MAX_TOKENS", usage_metadata=None)
    )

    with pytest.raises(ProviderOutputRejectedError) as excinfo:
        asyncio.run(_generate(adapter))

    error = excinfo.value
    # Ausência continua ausência: nada é inventado.
    assert error.input_tokens is None
    assert error.output_tokens is None
    assert error.total_tokens is None
    assert error.output_budget == BUDGET


def test_truncation_message_still_carries_no_generated_content(adapter, monkeypatch):
    partial = "conteudo_parcial_que_nao_pode_vazar"
    install_fake_sdk(
        monkeypatch,
        response(text=partial, finish_reason="MAX_TOKENS", usage_metadata=usage(1, 2, 3)),
    )

    with pytest.raises(ProviderOutputRejectedError) as excinfo:
        asyncio.run(_generate(adapter))

    assert partial not in str(excinfo.value)


# =====================================================================
# 3. Propagação até auditoria e observabilidade
# =====================================================================


@pytest.fixture
def enforced(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, REGISTRY)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    monkeypatch.delenv(FLAG_CIRCUIT_ENABLED, raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)


def _install_outcome(monkeypatch, outcome):
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
            answer="resposta sintética",
            provider="gemini",
            model=model,
            finish_reason="STOP",
            output_budget=output_budget,
            transport_timeout_ms=transport_timeout_ms,
            transport_close=TransportClose.CONFIRMED,
        )

    monkeypatch.setattr(GeminiProvider, "generate_response", fake)


def _post(**overrides):
    payload = {
        "message": "Como me organizo financeiramente?",
        "provider": "auto",
        "task_type": "finance_advice",
        "origin_system": "finguard",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    return client.post(
        "/api/orchestrate", json=payload, headers={AUTH_HEADER: FINGUARD_KEY}
    )


def test_audit_records_truncation_tokens(enforced, monkeypatch):
    _install_outcome(
        monkeypatch,
        ProviderOutputRejectedError(
            "truncada",
            finish_reason="MAX_TOKENS",
            truncated=True,
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
            output_budget=4096,
            transport_timeout_ms=27_000,
        ),
    )

    audit = _post().json()["audit"]
    attempt = audit["provider_attempts"][0]

    assert audit["provider_output_truncated"] is True
    assert audit["provider_input_tokens"] == 100
    assert audit["provider_output_tokens"] == 200
    assert audit["provider_total_tokens"] == 300
    assert attempt["finish_reason"] == "MAX_TOKENS"
    assert attempt["output_budget"] == 4096


def test_audit_never_claims_a_close_it_cannot_observe(enforced, monkeypatch):
    # Timeout da orquestração: a exceção vem do `wait_for`, não do adapter.
    # O PedroCore pediu o cancelamento, mas não observa o fechamento.
    _install_outcome(monkeypatch, TimeoutError("espera externa expirou"))

    audit = _post().json()["audit"]
    attempt = audit["provider_attempts"][0]

    assert attempt["transport_close_requested"] is True
    assert attempt["transport_close_outcome"] == TransportClose.UNKNOWN.value
    assert attempt["completion_certainty"] == "ambiguous"


def test_audit_records_a_failed_close_as_failed(enforced, monkeypatch):
    error = ProviderTransportTimeoutError("transporte expirou")
    error.transport_close = TransportClose.FAILED
    _install_outcome(monkeypatch, error)

    audit = _post().json()["audit"]
    attempt = audit["provider_attempts"][0]

    assert attempt["transport_close_requested"] is True
    assert attempt["transport_close_outcome"] == TransportClose.FAILED.value
    # Falha de fechamento jamais melhora a certeza de conclusão.
    assert attempt["completion_certainty"] == "ambiguous"


def test_audit_records_a_confirmed_close_as_confirmed(enforced, monkeypatch):
    error = ProviderTransportTimeoutError("transporte expirou")
    error.transport_close = TransportClose.CONFIRMED
    _install_outcome(monkeypatch, error)

    attempt = _post().json()["audit"]["provider_attempts"][0]

    assert attempt["transport_close_outcome"] == TransportClose.CONFIRMED.value
    # Confirmar o fechamento LOCAL continua não provando término remoto.
    assert attempt["completion_certainty"] == "ambiguous"


def test_success_records_a_confirmed_close(enforced, monkeypatch):
    _install_outcome(monkeypatch, None)

    attempt = _post().json()["audit"]["provider_attempts"][0]

    assert attempt["transport_close_outcome"] == TransportClose.CONFIRMED.value
    assert attempt["completion_certainty"] == "completed"


def test_finance_advice_budget_is_the_conversational_cap(enforced, monkeypatch):
    _install_outcome(monkeypatch, None)

    audit = _post().json()["audit"]

    assert audit["output_budget_effective"] == output_budget_service.task_cap(
        "finance_advice"
    )
    assert audit["output_budget_effective"] == 4096
