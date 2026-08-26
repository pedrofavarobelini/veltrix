"""Contrato oficial, mínimo e fail-closed do consumer textual Elyra V1.

A suíte padrão é integralmente sintética e não usa rede. O único teste capaz
de chegar ao Gemini real é opt-in por flag exclusiva e fica skipped no CI.
"""

from __future__ import annotations

import copy
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.schemas import CallerRole, IdentityStrength
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
    caller_identity_service,
)
from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.elyra_textual.idempotency import elyra_idempotency_service
from app.modules.elyra_multimodal.schemas import ELYRA_MULTIMODAL_TASK_TYPE
from app.modules.elyra_textual.schemas import (
    ELYRA_CANONICAL_MESSAGE,
    ELYRA_CONTRACT_VERSION,
    ELYRA_INPUT_SCHEMA_VERSION,
    ELYRA_OPERATION,
    ELYRA_OUTPUT_SCHEMA_VERSION,
    ELYRA_TASK_TYPE,
    ElyraTextualInputV1,
)
from app.modules.elyra_textual.service import elyra_textual_service
from app.modules.orchestration.service import orchestration_service
from app.modules.provider_authorization.schemas import AuthorizationResult
from app.modules.provider_authorization.service import provider_authorization_service
from app.modules.provider_health.service import provider_health_service
from app.modules.providers.base import ProviderResponse
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.project_context.service import project_context_resolver
from app.modules.real_features.service import FLAG_RUN_REAL_ELYRA_TESTS
from app.modules.task_router.service import task_router
from tests.real_flags import optin

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
ELYRA_CREDENTIAL = "elyra-contract-test-credential"
ELYRA_TECHNICAL_CREDENTIAL = "elyra-technical-denied-credential"
ELYRA_PRODUCTION_CREDENTIAL = "elyra-production-denied-credential"
FAKE_GEMINI_KEY = "elyra-offline-key-never-dispatched"


@pytest.fixture(autouse=True)
def isolated_elyra_state(monkeypatch):
    elyra_idempotency_service.clear()
    provider_health_service.reset()
    monkeypatch.setenv("PEDROCORE_PROVIDER_ROUTING_MODE", "legacy")
    monkeypatch.delenv("PEDROCORE_REAL_FALLBACK_ENABLED", raising=False)
    yield
    provider_health_service.reset()
    elyra_idempotency_service.clear()


@pytest.fixture
def elyra_registry(monkeypatch):
    registry = [
        {
            "credential_id": "elyra-textual-v1",
            "api_key": ELYRA_CREDENTIAL,
            "project_id": "elyra",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["elyra"],
        },
        {
            "credential_id": "elyra-technical-denied",
            "api_key": ELYRA_TECHNICAL_CREDENTIAL,
            "project_id": "elyra",
            "role": "technical_tool",
            "environment": "development",
            "allowed_origins": ["elyra"],
        },
        {
            "credential_id": "elyra-production-denied",
            "api_key": ELYRA_PRODUCTION_CREDENTIAL,
            "project_id": "elyra",
            "role": "common_consumer",
            "environment": "production",
            "allowed_origins": ["elyra"],
        },
    ]
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, json.dumps(registry))
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_GEMINI_KEY)
    return registry


def _comparison(current: float, previous: float, samples: int = 28) -> dict:
    delta = current - previous
    trend = "stable" if delta == 0 else ("up" if delta > 0 else "down")
    return {
        "current": current,
        "previous": previous,
        "delta": delta,
        "trend": trend,
        "currentSamples": samples,
        "previousSamples": samples,
    }


def _report() -> dict:
    first = date(2026, 7, 29)
    last = first + timedelta(days=27)
    series = [
        {
            "date": (first + timedelta(days=index)).isoformat(),
            "mood": 7.0,
            "anxiety": 3.0,
            "energy": 6.0,
            "sleepHours": 7.5,
            "moodHeatmapBucket": 3,
        }
        for index in range(28)
    ]
    return {
        "schemaVersion": "report_snapshot/v1",
        "analyticsVersion": "elyra-analytics/v1",
        "cycleHeuristicVersion": "elyra-cycle/v1",
        "timeZone": "America/Sao_Paulo",
        "window": {"from": first.isoformat(), "to": last.isoformat()},
        "previousWindow": {"from": "2026-07-01", "to": "2026-07-28"},
        "series": series,
        "metrics": {
            "mood": _comparison(7.0, 6.5),
            "anxiety": _comparison(3.0, 3.5),
            "energy": _comparison(6.0, 6.0),
            "sleepDurationMinutes": _comparison(450.0, 430.0),
        },
        "cycle": {
            "enabled": False,
            "registeredMenstruationDays": None,
            "registeredBands": [],
        },
        "associations": {
            "prePeriodEnergy": {
                "status": "insufficient_data",
                "metric": "energy",
                "beforePeriodMean": None,
                "otherDaysMean": None,
                "delta": None,
                "beforePeriodSamples": 0,
                "otherDaysSamples": 0,
            }
        },
        "dataQuality": {
            "daysInWindow": 28,
            "daysWithMood": 28,
            "daysWithAnxiety": 28,
            "daysWithEnergy": 28,
            "daysWithSleep": 28,
        },
    }


def _payload(**overrides) -> dict:
    payload = {
        "message": ELYRA_CANONICAL_MESSAGE,
        "mode": "tecnico",
        "provider": "mock",
        "task_type": ELYRA_TASK_TYPE,
        "origin_system": "elyra",
        "allow_real_provider": False,
        "allow_mock_fallback": True,
        "correlation_id": "elyra-stage09-request-001",
        "idempotency_key": "elyra-stage09-idempotency-001",
        "context": {
            "contractVersion": ELYRA_CONTRACT_VERSION,
            "inputSchemaVersion": ELYRA_INPUT_SCHEMA_VERSION,
            "operation": ELYRA_OPERATION,
            "aiInferenceConsent": True,
            "report": _report(),
        },
    }
    payload.update(overrides)
    return payload


def _post(credential: str | None = ELYRA_CREDENTIAL, **overrides):
    headers = {AUTH_HEADER: credential} if credential else {}
    return client.post(
        "/api/orchestrate",
        json=_payload(**overrides),
        headers=headers,
    )


def _registered_context(credential: str):
    resolution = caller_identity_service.resolve(credential)
    assert resolution.rejected is False
    assert resolution.context is not None
    return resolution.context


def _valid_output(correlation_id: str) -> str:
    request = ElyraTextualInputV1.model_validate(_payload()["context"])
    output = elyra_textual_service.deterministic_mock(request, correlation_id)
    return elyra_textual_service.serialize_output(output)


def test_project_context_and_task_registry_expose_only_narrow_elyra_capabilities():
    """A allowlist Elyra continua estreita e explicita.

    A Stage 12 acrescentou UMA capability multimodal propria. O teste protege o
    que importa: a lista e fechada, nominal e nao concede escrita, execucao,
    leitura de repositorio nem qualquer task generica.
    """
    project = project_context_resolver.resolve("Elyra")
    strategy = task_router.resolve(ELYRA_TASK_TYPE)

    assert project.project_id == "elyra"
    assert project.allowed_tasks == [
        ELYRA_TASK_TYPE,
        ELYRA_MULTIMODAL_TASK_TYPE,
    ]
    assert project.read_only is True
    assert project.can_execute_commands is False
    assert project.can_write_files is False
    assert "diagnostica" in (project.notes or "")
    assert "Learning " in (project.notes or "")
    assert "permanece desabilitado" in (project.notes or "")
    assert strategy.response_style == "elyra_textual_v1"
    assert strategy.requires_structured_response is True
    assert strategy.criticality == "high"


def test_elyra_multimodal_task_is_registered_with_its_own_strategy():
    """A capability multimodal nao reaproveita o response_style textual."""
    strategy = task_router.resolve(ELYRA_MULTIMODAL_TASK_TYPE)

    assert strategy.task_type == ELYRA_MULTIMODAL_TASK_TYPE
    assert strategy.response_style == "elyra_multimodal_v1"
    assert strategy.requires_structured_response is True
    assert strategy.criticality == "high"
    assert strategy.warnings == []


def test_registered_elyra_common_consumer_and_provider_matrix(elyra_registry):
    caller = _registered_context(ELYRA_CREDENTIAL)
    project = project_context_resolver.resolve("elyra")
    claim = caller_identity_service.validate_origin_claim(caller, "elyra", project.project_id)
    decision = provider_authorization_service.evaluate(
        identity_strength=caller.identity_strength,
        project_id=claim.identity_project_id,
        caller_role=caller.caller_role,
        environment=caller.environment,
        provider_id="gemini",
    )

    assert caller.identity_strength is IdentityStrength.REGISTERED
    assert caller.project_id == "elyra"
    assert caller.caller_role is CallerRole.COMMON_CONSUMER
    assert caller.allowed_origins == ("elyra",)
    assert claim.rejected is False
    assert decision.result is AuthorizationResult.ALLOWED


@pytest.mark.parametrize(
    ("credential", "provider_id"),
    [
        (ELYRA_TECHNICAL_CREDENTIAL, "gemini"),
        (ELYRA_PRODUCTION_CREDENTIAL, "gemini"),
        (ELYRA_CREDENTIAL, "openai"),
        (ELYRA_CREDENTIAL, "claude"),
        (ELYRA_CREDENTIAL, "deepseek"),
        (ELYRA_CREDENTIAL, "grok"),
    ],
)
def test_provider_matrix_denies_unlisted_role_environment_and_providers(
    elyra_registry, credential, provider_id
):
    caller = _registered_context(credential)
    decision = provider_authorization_service.evaluate(
        identity_strength=caller.identity_strength,
        project_id="elyra",
        caller_role=caller.caller_role,
        environment=caller.environment,
        provider_id=provider_id,
    )

    assert decision.denied is True


def test_existing_provider_authorization_rules_remain_available(elyra_registry):
    decisions = [
        provider_authorization_service.evaluate(
            identity_strength=IdentityStrength.REGISTERED,
            project_id="finguard",
            caller_role=CallerRole.COMMON_CONSUMER,
            environment="development",
            provider_id="gemini",
        ),
        provider_authorization_service.evaluate(
            identity_strength=IdentityStrength.REGISTERED,
            project_id="structa",
            caller_role=CallerRole.TECHNICAL_TOOL,
            environment="development",
            provider_id="gemini",
        ),
        provider_authorization_service.evaluate(
            identity_strength=IdentityStrength.LOCAL_TRUSTED,
            project_id="pedrocore",
            caller_role=CallerRole.TECHNICAL_TOOL,
            environment="development",
            provider_id="gemini",
        ),
    ]

    assert all(item.result is AuthorizationResult.ALLOWED for item in decisions)


def test_valid_mock_contract_is_structured_correlated_and_offline(
    elyra_registry, real_provider_guard
):
    response = _post()
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["project_id"] == "elyra"
    assert data["provider_requested"] == "mock"
    assert data["provider_used"] == "mock"
    assert data["model"] == "mock-v1"
    assert data["fallback_used"] is False
    assert data["correlation_id"] == "elyra-stage09-request-001"
    assert data["elyra"]["contractVersion"] == ELYRA_CONTRACT_VERSION
    assert data["elyra"]["outputSchemaVersion"] == ELYRA_OUTPUT_SCHEMA_VERSION
    assert data["elyra"]["correlationId"] == data["correlation_id"]
    assert data["answer"] == data["elyra"]["summary"]
    assert set(data["elyra"]["safety"].values()) == {False}
    assert data["audit"]["project_id_authenticated"] == "elyra"
    assert data["audit"]["correlation_id"] == data["correlation_id"]
    assert data["audit"]["idempotency_key_id"].startswith("idem_")
    assert _payload()["idempotency_key"] not in response.text
    assert real_provider_guard == []


def test_missing_and_unknown_caller_are_denied_before_provider(
    elyra_registry, real_provider_guard
):
    missing = _post(None)
    unknown = _post("unknown-elyra-credential")

    assert missing.status_code == 401
    assert missing.json()["error_code"] == codes.CALLER_CREDENTIAL_MISSING
    assert missing.json()["correlation_id"] == "elyra-stage09-request-001"
    assert unknown.status_code == 401
    assert unknown.json()["error_code"] == codes.CALLER_CREDENTIAL_UNKNOWN
    assert real_provider_guard == []


def test_origin_mismatch_is_denied_before_provider(elyra_registry, real_provider_guard):
    data = _post(origin_system="pedrocore").json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.CALLER_ORIGIN_MISMATCH
    assert data["provider_used"] == "none"
    assert data["correlation_id"] == "elyra-stage09-request-001"
    assert real_provider_guard == []


@pytest.mark.parametrize("credential", [ELYRA_TECHNICAL_CREDENTIAL, None])
def test_elyra_requires_registered_common_consumer(
    elyra_registry, monkeypatch, real_provider_guard, credential
):
    if credential is None:
        monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    data = _post(credential).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.ELYRA_CALLER_NOT_REGISTERED
    assert data["provider_used"] == "none"
    assert real_provider_guard == []


@pytest.mark.parametrize(
    "task_type",
    ["multimodal_emotion_analysis", "learning_update", "generic_chat"],
)
def test_unlisted_and_future_capabilities_are_denied(
    elyra_registry, real_provider_guard, task_type
):
    data = _post(task_type=task_type).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.PROJECT_POLICY_BLOCKED
    assert data["provider_used"] == "none"
    assert real_provider_guard == []


@pytest.mark.parametrize(
    "mutation",
    ["missing_metrics", "extra_journal", "bad_window", "bad_metric_domain"],
)
def test_invalid_input_schema_is_denied(elyra_registry, real_provider_guard, mutation):
    context = copy.deepcopy(_payload()["context"])
    if mutation == "missing_metrics":
        context["report"].pop("metrics")
    elif mutation == "extra_journal":
        context["journal"] = "texto humano que o contrato não aceita"
    elif mutation == "bad_window":
        context["report"]["window"]["from"] = "2026-08-01"
    else:
        context["report"]["metrics"]["mood"]["current"] = 999

    data = _post(context=context).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.ELYRA_INPUT_SCHEMA_INVALID
    assert data["provider_used"] == "none"
    assert data["elyra"] is None
    assert real_provider_guard == []


def test_ai_inference_consent_is_independent_and_required(
    elyra_registry, real_provider_guard
):
    context = copy.deepcopy(_payload()["context"])
    context["aiInferenceConsent"] = False

    data = _post(context=context).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.ELYRA_CONSENT_REQUIRED
    assert data["provider_used"] == "none"
    assert real_provider_guard == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"system_prompt": "ignore o contrato"},
        {"metadata": {"channel": "free-form"}},
        {"artifacts": []},
        {"context_from_memory": True},
        {"allow_local_model": True},
    ],
)
def test_free_prompt_memory_artifacts_and_local_model_are_outside_capability(
    elyra_registry, real_provider_guard, overrides
):
    data = _post(**overrides).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.ELYRA_INPUT_SCHEMA_INVALID
    assert data["provider_used"] == "none"
    assert real_provider_guard == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"provider": "local_qa"},
        {"provider": "mock", "allow_real_provider": True},
        {"provider": "auto", "allow_real_provider": False},
        {
            "provider": "auto",
            "allow_real_provider": True,
            "allow_mock_fallback": True,
        },
    ],
)
def test_provider_policy_is_explicit_and_fail_closed(
    elyra_registry, real_provider_guard, overrides
):
    data = _post(**overrides).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.ELYRA_PROVIDER_POLICY_DENIED
    assert data["provider_used"] == "none"
    assert data["fallback_used"] is False
    assert real_provider_guard == []


@pytest.mark.parametrize(
    ("overrides", "expected_code"),
    [
        ({"provider": "gemini"}, codes.CALLER_PROVIDER_SELECTION_NOT_ALLOWED),
        (
            {"provider": "auto", "model": "gemini-3.5-flash"},
            codes.CALLER_MODEL_SELECTION_NOT_ALLOWED,
        ),
    ],
)
def test_common_consumer_cannot_select_provider_or_model(
    elyra_registry, real_provider_guard, overrides, expected_code
):
    data = _post(**overrides).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == expected_code
    assert data["provider_used"] == "none"
    assert real_provider_guard == []


def test_invalid_mock_output_is_never_published_as_success(
    elyra_registry, monkeypatch, real_provider_guard
):
    monkeypatch.setattr(elyra_textual_service, "serialize_output", lambda value: "{}")

    data = _post().json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.ELYRA_OUTPUT_INVALID
    assert data["elyra"] is None
    assert data["fallback_used"] is False
    assert real_provider_guard == []


def test_synthetic_real_provider_returns_valid_versioned_output(
    elyra_registry, monkeypatch, real_provider_guard
):
    calls = []

    async def success(
        self, message, mode, model=None, system_prompt=None, **kwargs
    ) -> ProviderResponse:
        calls.append((model, system_prompt))
        return ProviderResponse(
            answer=_valid_output("elyra-stage09-request-001"),
            provider="gemini",
            model=model,
        )

    monkeypatch.setattr(GeminiProvider, "generate_response", success)
    data = _post(
        provider="auto",
        allow_real_provider=True,
        allow_mock_fallback=False,
    ).json()

    assert data["status"] == "ok"
    assert data["provider_requested"] == "auto"
    assert data["provider_used"] == "gemini"
    assert data["model"] == settings.gemini_model
    assert data["fallback_used"] is False
    assert data["elyra"]["outputSchemaVersion"] == ELYRA_OUTPUT_SCHEMA_VERSION
    assert data["audit"]["real_provider_attempt_count"] == 1
    assert len(calls) == 1
    assert ELYRA_CONTRACT_VERSION in calls[0][1]
    assert real_provider_guard == []


@pytest.mark.parametrize(
    ("responding_provider", "responding_model"),
    [("openai", None), ("gemini", "unregistered-model")],
)
def test_provider_or_model_mismatch_is_refused_without_fallback(
    elyra_registry,
    monkeypatch,
    real_provider_guard,
    responding_provider,
    responding_model,
):
    async def mismatched(
        self, message, mode, model=None, system_prompt=None, **kwargs
    ) -> ProviderResponse:
        return ProviderResponse(
            answer=_valid_output("elyra-stage09-request-001"),
            provider=responding_provider,
            model=responding_model or model,
        )

    monkeypatch.setattr(GeminiProvider, "generate_response", mismatched)
    data = _post(
        provider="auto",
        allow_real_provider=True,
        allow_mock_fallback=False,
    ).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.ELYRA_PROVIDER_MISMATCH
    assert data["elyra"] is None
    assert data["fallback_used"] is False
    assert data["audit"]["real_provider_attempt_count"] == 1
    assert real_provider_guard == []


def test_invalid_real_output_is_refused_without_partial_success(
    elyra_registry, monkeypatch, real_provider_guard
):
    async def invalid(
        self, message, mode, model=None, system_prompt=None, **kwargs
    ) -> ProviderResponse:
        return ProviderResponse(answer="{\"summary\": \"incompleto\"}", provider="gemini", model=model)

    monkeypatch.setattr(GeminiProvider, "generate_response", invalid)
    data = _post(
        provider="auto",
        allow_real_provider=True,
        allow_mock_fallback=False,
    ).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.ELYRA_OUTPUT_INVALID
    assert data["elyra"] is None
    assert data["fallback_used"] is False
    assert real_provider_guard == []


def test_timeout_is_controlled_and_never_retried(
    elyra_registry, monkeypatch, real_provider_guard
):
    calls = []

    async def timeout(
        self, message, mode, model=None, system_prompt=None, **kwargs
    ) -> ProviderResponse:
        calls.append("gemini")
        raise TimeoutError("timeout sintético após dispatch")

    monkeypatch.setattr(GeminiProvider, "generate_response", timeout)
    data = _post(
        provider="auto",
        allow_real_provider=True,
        allow_mock_fallback=False,
    ).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.PROVIDER_TIMEOUT
    assert data["provider_used"] == "none"
    assert data["fallback_used"] is False
    assert data["elyra"] is None
    assert calls == ["gemini"]
    assert data["audit"]["real_provider_attempt_count"] == 1
    assert data["audit"]["real_fallback_attempted"] is False
    assert real_provider_guard == []


def test_provider_unavailable_is_explicit_and_does_not_fallback(
    elyra_registry, monkeypatch, real_provider_guard
):
    monkeypatch.setattr(settings, "gemini_api_key", "")

    data = _post(
        provider="auto",
        allow_real_provider=True,
        allow_mock_fallback=False,
    ).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.PROVIDER_REAL_UNAVAILABLE
    assert data["provider_used"] == "none"
    assert data["fallback_used"] is False
    assert data["audit"]["real_provider_attempt_count"] == 0
    assert real_provider_guard == []


def test_idempotency_replays_once_and_conflicts_on_changed_payload(
    elyra_registry, monkeypatch, real_provider_guard
):
    original = elyra_textual_service.deterministic_mock
    calls = []

    def counted(request, correlation_id):
        calls.append(correlation_id)
        return original(request, correlation_id)

    monkeypatch.setattr(elyra_textual_service, "deterministic_mock", counted)
    first = _post().json()
    replay = _post().json()
    conflict = _post(correlation_id="elyra-stage09-request-changed").json()

    assert first["status"] == replay["status"] == "ok"
    assert first["audit"]["audit_id"] == replay["audit"]["audit_id"]
    assert first["idempotency_replayed"] is False
    assert replay["idempotency_replayed"] is True
    assert replay["audit"]["idempotency_replayed"] is True
    assert conflict["status"] == "blocked"
    assert conflict["error_code"] == codes.ELYRA_IDEMPOTENCY_CONFLICT
    assert conflict["provider_used"] == "none"
    assert calls == ["elyra-stage09-request-001"]
    assert real_provider_guard == []


def test_concurrent_duplicate_requests_share_one_execution(
    elyra_registry, monkeypatch, real_provider_guard
):
    original = elyra_textual_service.deterministic_mock
    started = Event()
    release = Event()
    calls = []

    def slow(request, correlation_id):
        calls.append(correlation_id)
        started.set()
        assert release.wait(2)
        return original(request, correlation_id)

    monkeypatch.setattr(elyra_textual_service, "deterministic_mock", slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(_post)
        assert started.wait(2)
        second = pool.submit(_post)
        release.set()
        responses = [first.result(timeout=3).json(), second.result(timeout=3).json()]

    assert all(item["status"] == "ok" for item in responses)
    assert sorted(item["idempotency_replayed"] for item in responses) == [False, True]
    assert calls == ["elyra-stage09-request-001"]
    assert real_provider_guard == []


def test_internal_failure_is_blocked_without_exception_or_success(
    elyra_registry, monkeypatch, real_provider_guard
):
    async def fail(payload: ChatRequest, caller):
        raise RuntimeError("detalhe interno sintético que não deve vazar")

    monkeypatch.setattr(orchestration_service, "_execute_pipeline", fail)
    data = _post().json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.ELYRA_INTERNAL_FAILURE
    assert data["provider_used"] == "unknown"
    assert data["fallback_used"] is False
    assert data["elyra"] is None
    assert "detalhe interno" not in json.dumps(data)
    assert real_provider_guard == []


def test_shared_contract_additions_are_backward_compatible():
    request = ChatRequest(message="consumer legado")

    assert request.correlation_id is None
    assert request.idempotency_key is None
    assert request.provider == "mock"
    assert request.allow_real_provider is False
    assert request.allow_mock_fallback is True


@optin(FLAG_RUN_REAL_ELYRA_TESTS)
def test_real_elyra_gemini_once_without_fallback():
    credential = (os.environ.get("PEDROCORE_ELYRA_QA_CREDENTIAL") or "").strip()
    assert credential, "PEDROCORE_ELYRA_QA_CREDENTIAL é obrigatória no teste real opt-in"
    correlation = f"elyra-real-{uuid4()}"
    idempotency = f"elyra-real-{uuid4()}"

    response = _post(
        credential,
        provider="auto",
        allow_real_provider=True,
        allow_mock_fallback=False,
        correlation_id=correlation,
        idempotency_key=idempotency,
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["project_id"] == "elyra"
    assert data["task_type"] == ELYRA_TASK_TYPE
    assert data["provider_requested"] == "auto"
    assert data["provider_used"] == "gemini"
    assert data["model"] == settings.gemini_model
    assert data["fallback_used"] is False
    assert data["correlation_id"] == correlation
    assert data["elyra"]["correlationId"] == correlation
    assert data["audit"]["real_provider_attempt_count"] == 1
    assert data["audit"]["orchestration_timeout_ms"] > 0
    assert data["audit"]["transport_timeout_ms"] > 0
