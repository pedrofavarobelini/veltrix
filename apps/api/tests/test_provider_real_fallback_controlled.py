"""Etapa 7: fallback real controlado, sequencial e somente pre-dispatch.

Todos os adapters externos são substituídos por fakes. O segundo e o terceiro
provider só são homologados/autorizados dentro do escopo do teste; o catálogo
de produção continua Gemini-only.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from time import perf_counter

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.schemas import CallerRole, IdentityStrength
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.orchestration.schemas import OrchestrateResponse
from app.modules.orchestration.service import (
    FLAG_REAL_FALLBACK_ENABLED,
    MAX_REAL_PROVIDER_ATTEMPTS,
    REAL_FALLBACK_ALLOWED_TASKS,
)
from app.modules.provider_authorization import service as authorization_module
from app.modules.provider_catalog import service as catalog_module
from app.modules.provider_catalog.schemas import HomologationStatus
from app.modules.provider_health.schemas import FailureClassification
from app.modules.provider_health.service import (
    FLAG_CIRCUIT_ENABLED,
    provider_health_service,
)
from app.modules.providers.base import (
    ProviderConfigError,
    ProviderExecutionError,
    ProviderResponse,
)
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.openai_provider import OpenAIProvider
from app.modules.shadow_routing.schemas import EliminationReason, RoutingMode
from app.modules.shadow_routing.service import (
    FLAG_ROUTING_MODE,
    shadow_routing_service,
)

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FINGUARD_KEY = "finguard-stage7-registered"
SHARED_KEY = "stage7-shared-ambiguous"
FAKE_PROVIDER_KEY = "stage7-synthetic-never-real"

REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-stage7",
            "api_key": FINGUARD_KEY,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
        }
    ]
)


class AdapterHarness:
    """Spies determinísticos que acusam ordem e eventual sobreposição."""

    def __init__(self, behavior: dict[str, str] | None = None) -> None:
        self.behavior = behavior or {}
        self.calls: list[str] = []
        self.timeline: list[tuple[str, str, float]] = []
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def install(self, monkeypatch) -> "AdapterHarness":
        for provider_class in (GeminiProvider, ClaudeProvider, OpenAIProvider):
            monkeypatch.setattr(
                provider_class,
                "generate_response",
                self._fake(provider_class.name),
            )
        return self

    def _fake(self, provider_name: str):
        async def generate(self_provider, message, mode, model, system_prompt=None, **kwargs):
            del self_provider, message, mode, system_prompt
            self.calls.append(provider_name)
            self.timeline.append(("start", provider_name, perf_counter()))
            behavior = self.behavior.get(provider_name, "success")

            if behavior == "config":
                self.timeline.append(("finish", provider_name, perf_counter()))
                raise ProviderConfigError(
                    f"Configuração sintética ausente para {provider_name}."
                )
            if behavior == "timeout":
                self.timeline.append(("finish", provider_name, perf_counter()))
                raise TimeoutError(f"Timeout sintético de {provider_name}.")

            with self._lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                if behavior == "execution":
                    raise ProviderExecutionError(
                        f"Falha sintética de execução de {provider_name}."
                    )
                return ProviderResponse(
                    answer=f"Resposta sintética de {provider_name}.",
                    provider=provider_name,
                    model=model,
                )
            finally:
                with self._lock:
                    self.active -= 1
                self.timeline.append(("finish", provider_name, perf_counter()))

        return generate


@pytest.fixture(autouse=True)
def reset_circuits():
    provider_health_service.reset()
    yield
    provider_health_service.reset()


@pytest.fixture
def stage7(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, REGISTRY)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    monkeypatch.setenv(FLAG_REAL_FALLBACK_ENABLED, "true")
    monkeypatch.delenv(FLAG_CIRCUIT_ENABLED, raising=False)

    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)
    monkeypatch.setattr(settings, "anthropic_api_key", FAKE_PROVIDER_KEY)
    monkeypatch.setattr(settings, "openai_api_key", FAKE_PROVIDER_KEY)

    specs = {
        provider_id: dict(spec)
        for provider_id, spec in catalog_module._STATIC_SPECS.items()
    }
    for provider_id in ("claude", "openai"):
        specs[provider_id]["homologation"] = HomologationStatus.HOMOLOGATED_REAL
        specs[provider_id]["authorized_for_auto"] = True
    monkeypatch.setattr(catalog_module, "_STATIC_SPECS", specs)

    models = tuple(
        entry.model_copy(update={"homologated": True, "authorized": True})
        if entry.provider_id in {"claude", "openai"}
        else entry
        for entry in catalog_module._MODEL_CATALOG
    )
    monkeypatch.setattr(catalog_module, "_MODEL_CATALOG", models)

    extra_rule = authorization_module.AuthorizationRule(
        identity_strengths=frozenset({IdentityStrength.REGISTERED}),
        project_ids=frozenset({"finguard"}),
        caller_roles=frozenset({CallerRole.COMMON_CONSUMER}),
        environments=frozenset({"development"}),
        providers=frozenset({"claude", "openai"}),
        notes="Somente teste sintético da Etapa 7.",
    )
    monkeypatch.setattr(
        authorization_module,
        "_RULES",
        (*authorization_module._RULES, extra_rule),
    )


def _post(credential: str = FINGUARD_KEY, **overrides):
    payload = {
        "message": "Pergunta sintética da Etapa 7.",
        "provider": "auto",
        "task_type": "assistant_chat",
        "origin_system": "finguard",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    return client.post(
        "/api/orchestrate",
        json=payload,
        headers={AUTH_HEADER: credential},
    )


def test_primary_success_stops_after_one_provider(stage7, monkeypatch):
    harness = AdapterHarness().install(monkeypatch)

    data = _post().json()

    assert data["provider_used"] == "gemini"
    assert data["fallback_used"] is False
    assert harness.calls == ["gemini"]
    assert len(data["audit"]["provider_attempts"]) == 1
    assert data["audit"]["real_fallback_attempted"] is False


def test_allow_mock_fallback_is_retrocompatible_and_defaults_to_true():
    request = ChatRequest(message="Contrato sintético retrocompatível.")

    assert request.allow_mock_fallback is True


def test_primary_success_ignores_disabled_mock_fallback(stage7, monkeypatch):
    harness = AdapterHarness().install(monkeypatch)

    data = _post(allow_mock_fallback=False).json()

    assert data["status"] == "ok"
    assert data["provider_used"] == "gemini"
    assert data["model"] == settings.gemini_model
    assert data["fallback_used"] is False
    assert data["error_code"] is None
    assert harness.calls == ["gemini"]
    assert data["audit"]["real_provider_attempt_count"] == 1
    assert data["audit"]["real_provider_attempt_record_count"] == 1


def test_ambiguous_timeout_with_mock_disabled_fails_closed_without_retry(
    stage7, monkeypatch
):
    harness = AdapterHarness({"gemini": "timeout"}).install(monkeypatch)

    data = _post(allow_mock_fallback=False).json()
    attempt = data["audit"]["provider_attempts"][0]

    assert data["status"] == "blocked"
    assert data["provider_requested"] == "auto"
    assert data["provider_used"] == "none"
    assert data["model"] == "none"
    assert data["fallback_used"] is False
    assert data["error_code"] == codes.PROVIDER_TIMEOUT
    assert data["blocked_reason"]
    assert codes.PROVIDER_COMPLETION_AMBIGUOUS in data["warning_codes"]
    assert harness.calls == ["gemini"]
    assert attempt["failure_classification"] == "completion_ambiguous"
    assert attempt["completion_certainty"] == "ambiguous"
    assert attempt["external_dispatch"] is True
    assert attempt["fallback_eligible"] is False
    assert data["audit"]["real_provider_attempt_count"] == 1
    assert data["audit"]["real_provider_attempt_record_count"] == 1
    assert data["audit"]["real_fallback_attempted"] is False


def test_authorization_denial_with_mock_disabled_reaches_zero_providers(
    stage7, monkeypatch
):
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, SHARED_KEY)
    harness = AdapterHarness().install(monkeypatch)

    data = _post(credential=SHARED_KEY, allow_mock_fallback=False).json()

    assert data["status"] == "blocked"
    assert data["provider_requested"] == "auto"
    assert data["provider_used"] == "none"
    assert data["model"] == "none"
    assert data["fallback_used"] is False
    assert data["error_code"] == codes.CALLER_IDENTITY_AMBIGUOUS
    assert harness.calls == []
    assert data["audit"]["provider_attempts"] == []
    assert data["audit"]["real_provider_attempt_count"] == 0


def test_safe_pre_dispatch_failure_uses_one_distinct_secondary_sequentially(
    stage7, monkeypatch
):
    harness = AdapterHarness({"gemini": "config"}).install(monkeypatch)

    data = _post().json()
    audit = data["audit"]
    attempts = audit["provider_attempts"]

    assert data["provider_used"] == "claude"
    assert data["fallback_used"] is True
    assert harness.calls == ["gemini", "claude"]
    assert harness.max_active == 1
    assert len(attempts) == MAX_REAL_PROVIDER_ATTEMPTS == 2
    assert len({item["provider_id"] for item in attempts}) == 2
    assert attempts[0]["failure_classification"] == "provider_pre_dispatch"
    assert attempts[0]["completion_certainty"] == "not_dispatched"
    assert attempts[0]["external_dispatch"] is False
    assert attempts[0]["fallback_eligible"] is True
    assert attempts[1]["external_dispatch"] is True
    assert attempts[1]["result"] == "success"
    assert datetime.fromisoformat(attempts[0]["finished_at"]) <= datetime.fromisoformat(
        attempts[1]["started_at"]
    )
    assert attempts[0]["request_id"] == attempts[1]["request_id"] == audit["audit_id"]
    assert attempts[0]["attempt_id"] != attempts[1]["attempt_id"]
    assert audit["real_provider_attempt_count"] == 1
    assert audit["real_provider_attempt_record_count"] == 2
    assert audit["real_fallback_attempted"] is True
    assert audit["routing_selected_provider"] == "gemini"
    assert audit["provider_selected"] == "claude"
    assert audit["real_fallback_candidates_considered"][0][
        "elimination_reason"
    ] == EliminationReason.ALREADY_ATTEMPTED.value
    assert audit["real_fallback_candidates_considered"][1]["provider_id"] == "claude"
    assert audit["real_fallback_candidates_considered"][1]["eliminated"] is False
    assert all(item["circuit_state_before"] == "closed" for item in attempts)


def test_provider_execution_error_is_not_safe_for_secondary(stage7, monkeypatch):
    harness = AdapterHarness({"gemini": "execution"}).install(monkeypatch)

    data = _post().json()
    attempt = data["audit"]["provider_attempts"][0]

    assert data["provider_used"] == "mock"
    assert harness.calls == ["gemini"]
    assert attempt["failure_classification"] == "provider_retryable"
    assert attempt["external_dispatch"] is True
    assert attempt["fallback_eligible"] is False
    assert data["audit"]["real_fallback_attempted"] is False


def test_internal_secondary_evaluation_error_fails_closed_to_mock(
    stage7, monkeypatch
):
    real_evaluate = shadow_routing_service.evaluate

    def fail_only_secondary(**kwargs):
        if kwargs.get("excluded_provider_ids"):
            raise RuntimeError("Falha sintética interna na segunda decisão.")
        return real_evaluate(**kwargs)

    monkeypatch.setattr(shadow_routing_service, "evaluate", fail_only_secondary)
    harness = AdapterHarness({"gemini": "config"}).install(monkeypatch)

    data = _post().json()

    assert data["provider_used"] == "mock"
    assert harness.calls == ["gemini"]
    assert data["audit"]["real_fallback_attempted"] is False
    assert "Mock seguro" in data["audit"]["real_fallback_reason"]


def test_ambiguous_timeout_never_starts_secondary_while_work_can_remain_alive(
    stage7, monkeypatch
):
    harness = AdapterHarness().install(monkeypatch)
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    worker_holder: list[threading.Thread] = []

    def lingering_work():
        started.set()
        release.wait(2)
        finished.set()

    async def timeout_with_live_external_work(
        self_provider, message, mode, model, system_prompt=None, **kwargs
    ):
        del self_provider, message, mode, model, system_prompt, kwargs
        harness.calls.append("gemini")
        worker = threading.Thread(target=lingering_work)
        worker_holder.append(worker)
        worker.start()
        assert started.wait(1)
        raise TimeoutError("Espera terminou; trabalho sintético continua.")

    monkeypatch.setattr(
        GeminiProvider,
        "generate_response",
        timeout_with_live_external_work,
    )

    try:
        data = _post().json()
        attempt = data["audit"]["provider_attempts"][0]

        assert data["provider_used"] == "mock"
        assert harness.calls == ["gemini"]
        assert worker_holder[0].is_alive()
        assert finished.is_set() is False
        assert attempt["failure_classification"] == "completion_ambiguous"
        assert attempt["completion_certainty"] == "ambiguous"
        assert attempt["external_dispatch"] is True
        assert attempt["fallback_eligible"] is False
        assert data["audit"]["real_fallback_attempted"] is False
    finally:
        release.set()
        for worker in worker_holder:
            worker.join(timeout=1)
        assert finished.is_set()


def test_caller_error_reaches_zero_providers(stage7, monkeypatch):
    harness = AdapterHarness().install(monkeypatch)

    data = _post(origin_system="pedrocore").json()

    assert data["provider_used"] == "none"
    assert harness.calls == []
    assert data["audit"]["provider_attempts"] == []


def test_policy_denial_reaches_zero_providers(stage7, monkeypatch):
    harness = AdapterHarness().install(monkeypatch)

    data = _post(task_type="report_ingestion").json()

    assert harness.calls == []
    assert data["audit"]["provider_attempts"] == []


def test_invalid_binding_reaches_zero_providers(stage7, monkeypatch):
    harness = AdapterHarness().install(monkeypatch)

    data = _post(model="modelo-controlado-pelo-consumidor").json()

    assert data["provider_used"] == "none"
    assert harness.calls == []
    assert data["audit"]["provider_attempts"] == []


def test_open_circuit_is_filtered_before_adapter_and_next_ranked_is_primary(
    stage7, monkeypatch
):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    key = provider_health_service.key(
        "development",
        "gemini",
        settings.gemini_model,
    )
    provider_health_service.record(
        key,
        FailureClassification.COMPLETION_AMBIGUOUS,
    )
    harness = AdapterHarness().install(monkeypatch)

    data = _post().json()

    assert data["provider_used"] == "claude"
    assert harness.calls == ["claude"]
    assert data["audit"]["real_fallback_attempted"] is False
    assert data["audit"]["routing_candidates_considered"][0][
        "elimination_reason"
    ] == EliminationReason.CIRCUIT_OPEN.value


def test_circuit_open_race_before_dispatch_can_use_safe_secondary(
    stage7, monkeypatch
):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    real_acquire = provider_health_service.acquire
    tripped = False

    def open_before_first_acquire(key):
        nonlocal tripped
        if key.provider_id == "gemini" and not tripped:
            tripped = True
            provider_health_service.record(
                key,
                FailureClassification.COMPLETION_AMBIGUOUS,
            )
        return real_acquire(key)

    monkeypatch.setattr(
        provider_health_service,
        "acquire",
        open_before_first_acquire,
    )
    harness = AdapterHarness().install(monkeypatch)

    data = _post().json()
    attempts = data["audit"]["provider_attempts"]

    assert data["provider_used"] == "claude"
    assert harness.calls == ["claude"]
    assert [item["provider_id"] for item in attempts] == ["gemini", "claude"]
    assert attempts[0]["result"] == "circuit_blocked"
    assert attempts[0]["external_dispatch"] is False
    assert attempts[0]["fallback_eligible"] is True
    assert data["audit"]["real_fallback_attempted"] is True


def test_secondary_failure_goes_to_mock_and_third_provider_never_runs(
    stage7, monkeypatch
):
    harness = AdapterHarness(
        {
            "gemini": "config",
            "claude": "execution",
            "openai": "success",
        }
    ).install(monkeypatch)

    data = _post().json()
    attempts = data["audit"]["provider_attempts"]

    assert data["provider_used"] == "mock"
    assert harness.calls == ["gemini", "claude"]
    assert len(attempts) == MAX_REAL_PROVIDER_ATTEMPTS
    assert attempts[1]["fallback_eligible"] is False
    assert data["audit"]["real_fallback_attempted"] is True


def test_kill_switch_is_default_off_and_payload_cannot_enable_it(
    stage7, monkeypatch
):
    monkeypatch.delenv(FLAG_REAL_FALLBACK_ENABLED, raising=False)
    harness = AdapterHarness({"gemini": "config"}).install(monkeypatch)

    data = _post(
        metadata={"real_fallback_enabled": True},
        context={"provider_fallback": "enabled"},
    ).json()

    assert "real_fallback_enabled" not in ChatRequest.model_fields
    assert data["provider_used"] == "mock"
    assert harness.calls == ["gemini"]
    assert data["audit"]["real_fallback_enabled"] is False
    assert data["audit"]["real_fallback_attempted"] is False


def test_task_outside_conservative_allowlist_never_uses_secondary(
    stage7, monkeypatch
):
    harness = AdapterHarness({"gemini": "config"}).install(monkeypatch)

    data = _post(task_type="project_status").json()

    assert "project_status" not in REAL_FALLBACK_ALLOWED_TASKS
    assert data["provider_used"] == "mock"
    assert harness.calls == ["gemini"]
    assert data["audit"]["real_fallback_attempted"] is False


def test_ambiguous_identity_never_uses_real_provider(stage7, monkeypatch):
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, SHARED_KEY)
    harness = AdapterHarness().install(monkeypatch)

    data = _post(credential=SHARED_KEY).json()

    assert data["provider_used"] == "mock"
    assert harness.calls == []
    assert data["audit"]["provider_attempts"] == []


def test_shadow_mode_keeps_fallback_without_effect(stage7, monkeypatch):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.SHADOW.value)
    harness = AdapterHarness({"gemini": "config"}).install(monkeypatch)

    data = _post().json()

    assert data["provider_used"] == "mock"
    assert harness.calls == ["gemini"]
    assert data["audit"]["routing_mode"] == RoutingMode.SHADOW.value
    assert data["audit"]["real_fallback_attempted"] is False


def test_finguard_contract_remains_additive_and_internal(stage7, monkeypatch):
    AdapterHarness({"gemini": "config"}).install(monkeypatch)

    data = _post().json()
    response = OrchestrateResponse.model_validate(data)

    assert response.provider_used == "claude"
    assert "real_fallback_enabled" not in OrchestrateResponse.model_fields
    assert "provider_attempts" not in OrchestrateResponse.model_fields


def test_live_catalog_still_has_only_gemini_homologated_for_auto():
    eligible = [
        item.provider_id
        for item in catalog_module.provider_catalog_service.definitions()
        if item.is_real_provider
        and item.is_approved_for_production
        and item.authorized_for_auto
    ]

    assert eligible == ["gemini"]
