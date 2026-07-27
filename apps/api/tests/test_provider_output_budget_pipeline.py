"""Pipeline com orçamento de saída, truncamento e término de geração.

Todos os adapters externos são substituídos por fakes; nenhuma chamada de rede
e nenhuma credencial real. O foco é o comportamento do PedroCore diante dos
novos estados, e a preservação das garantias já homologadas: uma IA por
requisição, sem retry, sem segundo provider após término não pre-dispatch.
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
from app.modules.contracts import codes
from app.modules.orchestration.service import (
    FLAG_REAL_FALLBACK_ENABLED,
    SAFE_FALLBACK_ANSWER,
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
)
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.shadow_routing.schemas import RoutingMode
from app.modules.shadow_routing.service import FLAG_ROUTING_MODE

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FINGUARD_KEY = "finguard-output-budget-registered"
FAKE_PROVIDER_KEY = "output-budget-synthetic-never-real"

REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-output-budget",
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


@pytest.fixture
def enforced(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, REGISTRY)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    monkeypatch.delenv(FLAG_REAL_FALLBACK_ENABLED, raising=False)
    monkeypatch.delenv(FLAG_CIRCUIT_ENABLED, raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)


class Spy:
    """Registra exatamente o que o pipeline entrega ao adapter."""

    def __init__(self, outcome=None) -> None:
        self.outcome = outcome
        self.calls: list[dict] = []

    def install(self, monkeypatch) -> "Spy":
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
            self.calls.append(
                {
                    "model": model,
                    "output_budget": output_budget,
                    "transport_timeout_ms": transport_timeout_ms,
                }
            )
            if isinstance(self.outcome, BaseException):
                raise self.outcome
            if self.outcome is not None:
                return self.outcome
            return ProviderResponse(
                answer="Resposta sintética completa.",
                provider="gemini",
                model=model,
                finish_reason="STOP",
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                output_budget=output_budget,
                transport_timeout_ms=transport_timeout_ms,
            )

        monkeypatch.setattr(GeminiProvider, "generate_response", fake)
        return self


def _post(**overrides):
    payload = {
        "message": "Como me organizo financeiramente?",
        "provider": "auto",
        "task_type": "assistant_chat",
        "origin_system": "finguard",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    return client.post(
        "/api/orchestrate", json=payload, headers={AUTH_HEADER: FINGUARD_KEY}
    )


# --------------------------------------------- orçamento chega até o adapter


def test_effective_budget_and_transport_timeout_reach_the_adapter(
    enforced, monkeypatch
):
    spy = Spy().install(monkeypatch)

    _post()

    assert len(spy.calls) == 1
    call = spy.calls[0]
    assert call["output_budget"] == output_budget_service.task_cap("assistant_chat")
    assert isinstance(call["transport_timeout_ms"], int)
    assert call["transport_timeout_ms"] > 0


def test_task_policy_changes_the_budget_delivered_to_the_adapter(
    enforced, monkeypatch
):
    spy = Spy().install(monkeypatch)

    _post(task_type="assistant_chat")
    _post(task_type="project_status")

    assert spy.calls[0]["output_budget"] == output_budget_service.task_cap(
        "assistant_chat"
    )
    assert spy.calls[1]["output_budget"] == output_budget_service.task_cap(
        "project_status"
    )


def test_consumer_cannot_influence_the_budget_through_the_payload(
    enforced, monkeypatch
):
    spy = Spy().install(monkeypatch)

    _post(
        metadata={"max_output_tokens": 999_999, "output_budget": 999_999},
        context={"max_tokens": 999_999},
    )

    assert spy.calls[0]["output_budget"] == output_budget_service.task_cap(
        "assistant_chat"
    )


def test_transport_timeout_is_strictly_below_the_orchestration_timeout(
    enforced, monkeypatch
):
    monkeypatch.setenv("PEDROCORE_PROVIDER_TIMEOUT_SECONDS", "30")
    spy = Spy().install(monkeypatch)

    data = _post().json()
    audit = data["audit"]

    assert audit["transport_timeout_ms"] < audit["orchestration_timeout_ms"]
    assert spy.calls[0]["transport_timeout_ms"] == audit["transport_timeout_ms"]


def test_audit_records_budget_composition_and_tokens(enforced, monkeypatch):
    Spy().install(monkeypatch)

    audit = _post().json()["audit"]

    assert audit["output_budget_effective"] == output_budget_service.task_cap(
        "assistant_chat"
    )
    assert audit["output_budget_source"] == "task_cap"
    assert audit["output_budget_global_cap"] == output_budget_service.global_cap()
    assert audit["output_budget_model_cap"] == 8192
    assert audit["provider_finish_reason"] == "STOP"
    assert audit["provider_input_tokens"] == 10
    assert audit["provider_output_tokens"] == 20
    assert audit["provider_total_tokens"] == 30
    assert audit["provider_output_truncated"] is False


def test_tokens_stay_absent_when_the_provider_does_not_report_them(
    enforced, monkeypatch
):
    Spy(
        ProviderResponse(
            answer="sem métricas", provider="gemini", model="gemini-3.5-flash"
        )
    ).install(monkeypatch)

    audit = _post().json()["audit"]

    assert audit["provider_input_tokens"] is None
    assert audit["provider_output_tokens"] is None
    assert audit["provider_total_tokens"] is None


# ------------------------------------------------------------- truncamento


def test_truncated_response_is_not_published_as_a_normal_answer(
    enforced, monkeypatch
):
    partial = "plano financeiro cortado na met"
    Spy(
        ProviderOutputRejectedError(
            "resposta truncada", finish_reason="MAX_TOKENS", truncated=True
        )
    ).install(monkeypatch)

    data = _post().json()

    assert data["answer"] == SAFE_FALLBACK_ANSWER
    assert partial not in data["answer"]
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert data["error_code"] == codes.PROVIDER_OUTPUT_TRUNCATED
    assert codes.PROVIDER_OUTPUT_TRUNCATED in data["warning_codes"]


def test_truncation_never_triggers_a_continuation_retry_or_second_provider(
    enforced, monkeypatch
):
    spy = Spy(
        ProviderOutputRejectedError(
            "resposta truncada", finish_reason="MAX_TOKENS", truncated=True
        )
    ).install(monkeypatch)

    data = _post().json()
    audit = data["audit"]

    assert len(spy.calls) == 1
    assert audit["real_provider_attempt_count"] == 1
    assert audit["real_provider_attempt_record_count"] == 1
    assert audit["real_fallback_attempted"] is False
    assert data["provider_used"] == "mock"


def test_truncation_is_recorded_as_completed_not_ambiguous(enforced, monkeypatch):
    Spy(
        ProviderOutputRejectedError(
            "resposta truncada", finish_reason="MAX_TOKENS", truncated=True
        )
    ).install(monkeypatch)

    audit = _post().json()["audit"]
    attempt = audit["provider_attempts"][0]

    # A chamada TERMINOU: a resposta chegou, só não é utilizável.
    assert attempt["completion_certainty"] == "completed"
    assert attempt["failure_classification"] == "provider_non_retryable"
    assert attempt["external_dispatch"] is True
    assert attempt["output_truncated"] is True
    assert attempt["finish_reason"] == "MAX_TOKENS"
    assert attempt["fallback_eligible"] is False
    assert audit["provider_output_truncated"] is True


def test_truncation_does_not_degrade_the_circuit(enforced, monkeypatch):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    Spy(
        ProviderOutputRejectedError(
            "resposta truncada", finish_reason="MAX_TOKENS", truncated=True
        )
    ).install(monkeypatch)

    attempt = _post().json()["audit"]["provider_attempts"][0]

    assert attempt["circuit_state_after"] == "closed"


def test_abnormal_finish_reason_uses_the_rejected_code(enforced, monkeypatch):
    Spy(
        ProviderOutputRejectedError(
            "condição anormal", finish_reason="SAFETY", truncated=False
        )
    ).install(monkeypatch)

    data = _post().json()

    assert data["error_code"] == codes.PROVIDER_OUTPUT_REJECTED
    assert data["provider_used"] == "mock"
    assert data["answer"] == SAFE_FALLBACK_ANSWER


# ------------------------------------------ timeout de transporte e término


def test_transport_timeout_keeps_the_stable_public_error_code(enforced, monkeypatch):
    Spy(ProviderTransportTimeoutError("transporte expirou")).install(monkeypatch)

    data = _post().json()

    # Contrato preservado: o consumidor continua vendo PROVIDER_TIMEOUT.
    assert data["error_code"] == codes.PROVIDER_TIMEOUT
    assert codes.PROVIDER_TIMEOUT in data["warning_codes"]


def test_transport_timeout_emits_the_ambiguity_warning(enforced, monkeypatch):
    Spy(ProviderTransportTimeoutError("transporte expirou")).install(monkeypatch)

    warning_codes = _post().json()["warning_codes"]

    assert codes.PROVIDER_TRANSPORT_TIMEOUT in warning_codes
    assert codes.PROVIDER_COMPLETION_AMBIGUOUS in warning_codes


def test_transport_timeout_completion_stays_ambiguous(enforced, monkeypatch):
    Spy(ProviderTransportTimeoutError("transporte expirou")).install(monkeypatch)

    attempt = _post().json()["audit"]["provider_attempts"][0]

    # Fechar a conexão local NÃO prova que a geração remota parou.
    assert attempt["completion_certainty"] == "ambiguous"
    assert attempt["failure_classification"] == "completion_ambiguous"
    assert attempt["external_dispatch"] is True


def test_local_transport_cancellation_is_recorded_without_claiming_remote_stop(
    enforced, monkeypatch
):
    Spy(ProviderTransportTimeoutError("transporte expirou")).install(monkeypatch)

    audit = _post().json()["audit"]
    attempt = audit["provider_attempts"][0]

    assert attempt["transport_cancel_requested"] is True
    assert attempt["transport_cancelled_locally"] is True
    # A convivência dos dois fatos é justamente o ponto: transporte fechado
    # localmente E conclusão remota desconhecida.
    assert attempt["completion_certainty"] == "ambiguous"
    assert audit["transport_cancelled_locally"] is True


def test_orchestration_timeout_also_stays_ambiguous(enforced, monkeypatch):
    Spy(TimeoutError("espera externa expirou")).install(monkeypatch)

    data = _post().json()
    attempt = data["audit"]["provider_attempts"][0]

    assert data["error_code"] == codes.PROVIDER_TIMEOUT
    assert attempt["completion_certainty"] == "ambiguous"
    assert codes.PROVIDER_COMPLETION_AMBIGUOUS in data["warning_codes"]


@pytest.mark.parametrize(
    "failure",
    [
        ProviderTransportTimeoutError("transporte expirou"),
        TimeoutError("espera externa expirou"),
    ],
)
def test_no_timeout_flavour_ever_starts_a_second_provider(
    enforced, monkeypatch, failure
):
    monkeypatch.setenv(FLAG_REAL_FALLBACK_ENABLED, "true")
    spy = Spy(failure).install(monkeypatch)

    audit = _post().json()["audit"]

    assert len(spy.calls) == 1
    assert audit["real_fallback_attempted"] is False
    assert audit["real_provider_attempt_count"] == 1


def test_timeout_and_truncation_never_produce_parallel_calls(enforced, monkeypatch):
    spy = Spy(ProviderTransportTimeoutError("transporte expirou")).install(monkeypatch)

    _post()

    assert len(spy.calls) == 1


# --------------------------------------------------------------- contratos


def test_success_contract_stays_backward_compatible(enforced, monkeypatch):
    Spy().install(monkeypatch)

    data = _post().json()

    for field in (
        "status",
        "answer",
        "provider_requested",
        "provider_used",
        "model",
        "fallback_used",
        "warning_codes",
        "audit",
    ):
        assert field in data
    assert data["provider_requested"] == "auto"
    assert data["provider_used"] == "gemini"
    assert data["fallback_used"] is False


def test_mock_path_has_no_budget_and_still_works(enforced, monkeypatch):
    data = _post(allow_real_provider=False).json()
    audit = data["audit"]

    assert data["provider_used"] == "mock"
    assert audit["output_budget_effective"] is None
    assert audit["transport_timeout_ms"] is None


def test_local_qa_path_is_untouched_by_the_budget_policy(enforced, monkeypatch):
    data = _post(
        provider="local_qa", task_type="qa_report_analysis", allow_real_provider=False
    ).json()

    assert data["provider_used"] == "local_qa"
    assert data["audit"]["output_budget_effective"] is None


def test_orchestration_delegates_to_the_single_derivation_rule():
    from app.modules.orchestration.service import OrchestrationService

    assert OrchestrationService._transport_timeout_ms(
        30.0
    ) == output_budget_service.transport_timeout_ms(30.0)


def test_only_gemini_receives_a_generation_budget():
    from app.modules.providers.registry import provider_registry

    supported = {
        name
        for name in ("mock", "gemini", "openai", "claude", "deepseek", "grok", "local_model")
        if getattr(provider_registry.get(name), "supports_generation_budget", False)
    }

    assert supported == {"gemini"}
