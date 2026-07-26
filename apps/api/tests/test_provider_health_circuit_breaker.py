"""Etapa 6: health state e circuit breaker determinísticos, sem rede."""

import asyncio
import json
import threading

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.contracts import codes
from app.modules.orchestration.schemas import OrchestrateResponse
from app.modules.orchestration.service import OrchestrationService
from app.modules.provider_health.schemas import (
    CircuitState,
    CompletionCertainty,
    FailureClassification,
)
from app.modules.provider_health.service import (
    FLAG_CIRCUIT_ENABLED,
    FLAG_COOLDOWN_SECONDS,
    FLAG_FAILURE_THRESHOLD,
    ProviderHealthService,
    provider_health_service,
)
from app.modules.providers.base import (
    ProviderConfigError,
    ProviderExecutionError,
    ProviderResponse,
)
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.openai_provider import OpenAIProvider
from app.modules.shadow_routing.schemas import EliminationReason, RoutingMode
from app.modules.shadow_routing.service import (
    FLAG_ROUTING_MODE,
    shadow_routing_service,
)

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FINGUARD_KEY = "finguard-stage6-registered"
FAKE_PROVIDER_KEY = "provider-stage6-synthetic-never-real"
REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-stage6",
            "api_key": FINGUARD_KEY,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
        }
    ]
)

REAL_PROVIDER_CLASSES = (
    GeminiProvider,
    OpenAIProvider,
    ClaudeProvider,
    DeepSeekProvider,
    GrokProvider,
)


class FakeClock:
    def __init__(self):
        self.now = 1_000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture(autouse=True)
def reset_global_health(monkeypatch):
    provider_health_service.reset()
    monkeypatch.delenv(FLAG_CIRCUIT_ENABLED, raising=False)
    monkeypatch.delenv(FLAG_FAILURE_THRESHOLD, raising=False)
    monkeypatch.delenv(FLAG_COOLDOWN_SECONDS, raising=False)
    yield
    provider_health_service.reset()


@pytest.fixture
def circuit(monkeypatch):
    clock = FakeClock()
    service = ProviderHealthService(clock=clock)
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    monkeypatch.setenv(FLAG_FAILURE_THRESHOLD, "2")
    monkeypatch.setenv(FLAG_COOLDOWN_SECONDS, "10")
    return service, clock


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, REGISTRY)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)


@pytest.fixture
def adapter_spy(monkeypatch):
    calls: list[tuple[str, str]] = []

    def install():
        def make(provider_name):
            async def fake(self, message, mode, model, system_prompt=None):
                calls.append((provider_name, model))
                return ProviderResponse(
                    answer=f"Resposta sintética de {provider_name}.",
                    provider=provider_name,
                    model=model,
                )

            return fake

        for provider_class in REAL_PROVIDER_CLASSES:
            monkeypatch.setattr(
                provider_class,
                "generate_response",
                make(provider_class.name),
            )
        return calls

    return install


def _key(service, provider="gemini", model="gemini-3.5-flash"):
    return service.key("development", provider, model)


def _post():
    return client.post(
        "/api/orchestrate",
        json={
            "message": "Pergunta sintética da Etapa 6.",
            "provider": "auto",
            "task_type": "assistant_chat",
            "origin_system": "finguard",
            "allow_real_provider": True,
        },
        headers={AUTH_HEADER: FINGUARD_KEY},
    )


def _context():
    return AuthenticatedCallerContext(
        credential_id="stage6-registered",
        caller_role=CallerRole.COMMON_CONSUMER,
        environment="development",
        identity_strength=IdentityStrength.REGISTERED,
        project_id="finguard",
        allowed_origins=("finguard",),
    )


def test_circuit_starts_closed(circuit):
    service, _ = circuit

    permit = service.acquire(_key(service))

    assert permit.allowed is True
    assert permit.snapshot.state is CircuitState.CLOSED
    assert permit.snapshot.consecutive_failures == 0


def test_success_keeps_closed_and_resets_failures(circuit):
    service, _ = circuit
    key = _key(service)
    service.record(key, FailureClassification.PROVIDER_RETRYABLE)

    snapshot = service.record(key, FailureClassification.SUCCESS)

    assert snapshot.state is CircuitState.CLOSED
    assert snapshot.consecutive_failures == 0


def test_retryable_failures_increment_and_threshold_opens(circuit):
    service, _ = circuit
    key = _key(service)

    first = service.record(key, FailureClassification.PROVIDER_RETRYABLE)
    second = service.record(key, FailureClassification.PROVIDER_RETRYABLE)

    assert first.state is CircuitState.CLOSED
    assert first.consecutive_failures == 1
    assert second.state is CircuitState.OPEN
    assert second.consecutive_failures == 2


def test_open_denies_without_reserving_an_attempt(circuit):
    service, _ = circuit
    key = _key(service)
    service.record(key, FailureClassification.COMPLETION_AMBIGUOUS)

    permit = service.acquire(key)

    assert permit.allowed is False
    assert permit.snapshot.state is CircuitState.OPEN
    assert permit.half_open_probe is False


def test_cooldown_transitions_to_half_open_without_sleep(circuit):
    service, clock = circuit
    key = _key(service)
    service.record(key, FailureClassification.COMPLETION_AMBIGUOUS)

    clock.advance(10)
    permit = service.acquire(key)

    assert permit.allowed is True
    assert permit.half_open_probe is True
    assert permit.snapshot.state is CircuitState.HALF_OPEN


def test_only_one_half_open_probe_is_allowed(circuit):
    service, clock = circuit
    key = _key(service)
    service.record(key, FailureClassification.COMPLETION_AMBIGUOUS)
    clock.advance(10)

    first = service.acquire(key)
    second = service.acquire(key)

    assert first.allowed is True
    assert first.half_open_probe is True
    assert second.allowed is False
    assert second.snapshot.half_open_probe_in_flight is True


def test_half_open_success_closes_and_failure_reopens(circuit):
    service, clock = circuit
    key = _key(service)
    service.record(key, FailureClassification.COMPLETION_AMBIGUOUS)
    clock.advance(10)
    success_probe = service.acquire(key)

    closed = service.record(
        key,
        FailureClassification.SUCCESS,
        half_open_probe=success_probe.half_open_probe,
    )
    service.record(key, FailureClassification.COMPLETION_AMBIGUOUS)
    clock.advance(10)
    failed_probe = service.acquire(key)
    reopened = service.record(
        key,
        FailureClassification.PROVIDER_RETRYABLE,
        half_open_probe=failed_probe.half_open_probe,
    )

    assert closed.state is CircuitState.CLOSED
    assert reopened.state is CircuitState.OPEN


@pytest.mark.parametrize(
    "classification",
    [
        FailureClassification.CALLER_ERROR,
        FailureClassification.POLICY_ERROR,
        FailureClassification.PROVIDER_NON_RETRYABLE,
        FailureClassification.PROVIDER_PRE_DISPATCH,
        FailureClassification.INTERNAL_ERROR,
    ],
)
def test_non_health_failures_do_not_contaminate_closed_circuit(
    circuit, classification
):
    service, _ = circuit

    snapshot = service.record(_key(service), classification)

    assert snapshot.state is CircuitState.CLOSED
    assert snapshot.consecutive_failures == 0


def test_timeout_has_explicit_ambiguous_classification():
    classification, certainty, dispatched = (
        OrchestrationService._classify_provider_failure(TimeoutError())
    )

    assert classification is FailureClassification.COMPLETION_AMBIGUOUS
    assert certainty is CompletionCertainty.AMBIGUOUS
    assert dispatched is True


def test_failure_taxonomy_is_not_derived_from_exception_text():
    retryable = OrchestrationService._classify_provider_failure(
        ProviderExecutionError("caller policy timeout words do not matter")
    )
    pre_dispatch = OrchestrationService._classify_provider_failure(
        ProviderConfigError("generic")
    )
    internal = OrchestrationService._classify_provider_failure(
        RuntimeError("provider timeout")
    )

    assert retryable[0] is FailureClassification.PROVIDER_RETRYABLE
    assert pre_dispatch[0] is FailureClassification.PROVIDER_PRE_DISPATCH
    assert internal[0] is FailureClassification.INTERNAL_ERROR


def test_wait_for_timeout_does_not_stop_to_thread_work():
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def work():
        started.set()
        release.wait()
        finished.set()

    async def scenario():
        task = asyncio.create_task(asyncio.to_thread(work))
        assert await asyncio.to_thread(started.wait, 1)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(task, timeout=0.01)
        assert finished.is_set() is False
        release.set()
        assert await asyncio.to_thread(finished.wait, 1)

    asyncio.run(scenario())


def test_half_open_concurrency_is_protected_by_lock(circuit):
    service, clock = circuit
    key = _key(service)
    service.record(key, FailureClassification.COMPLETION_AMBIGUOUS)
    clock.advance(10)
    barrier = threading.Barrier(3)
    results = []

    def acquire():
        barrier.wait()
        results.append(service.acquire(key).allowed)

    threads = [threading.Thread(target=acquire) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    assert sorted(results) == [False, True]


def test_provider_and_model_states_are_isolated(circuit):
    service, _ = circuit
    gemini = _key(service)
    claude = _key(service, provider="claude", model="claude-sonnet-4-5")
    other_model = _key(service, model="gemini-outro-modelo")
    service.record(gemini, FailureClassification.COMPLETION_AMBIGUOUS)

    assert service.peek(gemini).state is CircuitState.OPEN
    assert service.peek(claude).state is CircuitState.CLOSED
    assert service.peek(other_model).state is CircuitState.CLOSED


def test_shadow_consults_but_does_not_mutate_circuit(
    registry, monkeypatch
):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    monkeypatch.setenv(FLAG_FAILURE_THRESHOLD, "1")
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.SHADOW.value)
    key = provider_health_service.key(
        "development", "gemini", settings.gemini_model
    )
    provider_health_service.record(key, FailureClassification.PROVIDER_RETRYABLE)
    before = provider_health_service.peek(key)

    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )
    after = provider_health_service.peek(key)

    assert decision.candidates_considered[0].elimination_reason is (
        EliminationReason.CIRCUIT_OPEN
    )
    assert after.state is before.state
    assert after.consecutive_failures == before.consecutive_failures
    assert after.opened_at_monotonic == before.opened_at_monotonic
    assert after.half_open_probe_in_flight is before.half_open_probe_in_flight


def test_open_circuit_eliminates_enforced_candidate_without_adapter(
    registry, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    monkeypatch.setenv(FLAG_FAILURE_THRESHOLD, "1")
    calls = adapter_spy()
    key = provider_health_service.key(
        "development", "gemini", settings.gemini_model
    )
    provider_health_service.record(key, FailureClassification.PROVIDER_RETRYABLE)

    data = _post().json()

    assert data["provider_used"] == "mock"
    assert data["error_code"] == codes.PROVIDER_CIRCUIT_OPEN
    assert data["audit"]["real_provider_attempt_count"] == 0
    assert calls == []


def test_success_attempt_has_request_and_attempt_ids(
    registry, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    calls = adapter_spy()

    data = _post().json()
    attempts = data["audit"]["provider_attempts"]

    assert calls == [("gemini", settings.gemini_model)]
    assert len(attempts) == 1
    assert attempts[0]["request_id"] == data["audit"]["audit_id"]
    assert attempts[0]["attempt_id"]
    assert attempts[0]["ordinal"] == 1
    assert attempts[0]["failure_classification"] == "success"
    assert attempts[0]["circuit_state_before"] == "closed"
    assert attempts[0]["circuit_state_after"] == "closed"


def test_timeout_opens_circuit_and_records_ambiguous_completion(
    registry, monkeypatch
):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")

    async def timeout(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr(OrchestrationService, "_generate_with_timeout", timeout)

    data = _post().json()
    attempt = data["audit"]["provider_attempts"][0]

    assert data["provider_used"] == "mock"
    assert data["error_code"] == codes.PROVIDER_TIMEOUT
    assert attempt["failure_classification"] == "completion_ambiguous"
    assert attempt["completion_certainty"] == "ambiguous"
    assert attempt["circuit_state_after"] == "open"
    assert attempt["external_dispatch"] is True


def test_pre_dispatch_config_error_does_not_degrade_health(
    registry, monkeypatch
):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")

    async def config_error(*args, **kwargs):
        raise ProviderConfigError("Configuração sintética ausente.")

    monkeypatch.setattr(
        OrchestrationService,
        "_generate_with_timeout",
        config_error,
    )

    data = _post().json()
    attempt = data["audit"]["provider_attempts"][0]

    assert attempt["failure_classification"] == "provider_pre_dispatch"
    assert attempt["external_dispatch"] is False
    assert attempt["circuit_state_after"] == "closed"


def test_legacy_preserves_behavior_when_circuit_is_disabled(
    registry, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.LEGACY.value)
    monkeypatch.delenv(FLAG_CIRCUIT_ENABLED, raising=False)
    calls = adapter_spy()

    data = _post().json()

    assert data["provider_used"] == "gemini"
    assert data["audit"]["routing_mode"] == "legacy"
    assert data["audit"]["provider_attempts"][0]["circuit_state_before"] == "closed"
    assert calls == [("gemini", settings.gemini_model)]


def test_finguard_contract_remains_unchanged(
    registry, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    adapter_spy()

    data = _post().json()
    response = OrchestrateResponse.model_validate(data)

    assert response.answer
    assert "circuit_state" not in OrchestrateResponse.model_fields
    assert "failure_classification" not in OrchestrateResponse.model_fields
