"""Etapa 5: política única em shadow/enforced com uma chamada real no máximo.

Todos os adapters externos são substituídos por spies/fakes. Nenhum SDK ou
provider real é alcançado.
"""

import json

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
from app.modules.chat.schemas import ChatRequest
from app.modules.orchestration.schemas import OrchestrateResponse
from app.modules.provider_catalog import service as provider_catalog_module
from app.modules.providers.base import ProviderExecutionError, ProviderResponse
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.openai_provider import OpenAIProvider
from app.modules.shadow_routing.schemas import EliminationReason, RoutingMode
from app.modules.shadow_routing.service import (
    FLAG_ROUTING_MODE,
    FLAG_SHADOW_ROUTING,
    shadow_routing_service,
)

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FAKE_PROVIDER_KEY = "provider-stage5-synthetic-never-real"
FINGUARD_KEY = "finguard-stage5-registered"
TOOL_KEY = "pedrocore-stage5-tool"

REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-stage5",
            "api_key": FINGUARD_KEY,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
        },
        {
            "credential_id": "pedrocore-stage5",
            "api_key": TOOL_KEY,
            "project_id": "pedrocore",
            "role": "technical_tool",
            "environment": "development",
            "allowed_origins": ["pedrocore"],
        },
    ]
)

REAL_PROVIDER_CLASSES = (
    GeminiProvider,
    OpenAIProvider,
    ClaudeProvider,
    DeepSeekProvider,
    GrokProvider,
)


@pytest.fixture
def registry(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, REGISTRY)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)


@pytest.fixture
def all_configured(monkeypatch):
    for attribute in (
        "gemini_api_key",
        "anthropic_api_key",
        "openai_api_key",
        "deepseek_api_key",
        "xai_api_key",
    ):
        monkeypatch.setattr(settings, attribute, FAKE_PROVIDER_KEY)


@pytest.fixture
def adapter_spy(monkeypatch):
    calls: list[tuple[str, str | None]] = []

    def install(failing: set[str] | None = None):
        failing = failing or set()

        def make(provider_name: str):
            async def fake(self, message, mode, model, system_prompt=None):
                calls.append((provider_name, model))
                if provider_name in failing:
                    raise ProviderExecutionError(
                        f"Falha sintética controlada de {provider_name}."
                    )
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


def _post(credential=FINGUARD_KEY, **overrides):
    payload = {
        "message": "Pergunta sintética da Etapa 5.",
        "provider": "auto",
        "task_type": "assistant_chat",
        "origin_system": "finguard",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    headers = {AUTH_HEADER: credential} if credential else {}
    return client.post("/api/orchestrate", json=payload, headers=headers)


def _context(
    *,
    strength=IdentityStrength.REGISTERED,
    role=CallerRole.COMMON_CONSUMER,
    environment="development",
):
    if strength is IdentityStrength.AMBIGUOUS:
        return AuthenticatedCallerContext(
            credential_id="stage5-ambiguous",
            caller_role=CallerRole.COMMON_CONSUMER,
            environment=environment,
            identity_strength=strength,
            project_id="shared_or_unknown",
        )
    if strength is IdentityStrength.LOCAL_TRUSTED:
        return AuthenticatedCallerContext(
            credential_id="stage5-local",
            caller_role=CallerRole.TECHNICAL_TOOL,
            environment=environment,
            identity_strength=strength,
        )
    return AuthenticatedCallerContext(
        credential_id="stage5-registered",
        caller_role=role,
        environment=environment,
        identity_strength=strength,
        project_id="finguard",
        allowed_origins=("finguard",),
    )


def _candidate_signature(decision):
    return [
        (
            candidate.provider_id,
            candidate.model_id,
            candidate.eliminated,
            candidate.elimination_reason,
        )
        for candidate in decision.candidates_considered
    ]


def test_default_mode_is_legacy_and_preserves_previous_execution(
    registry, all_configured, monkeypatch, adapter_spy
):
    monkeypatch.delenv(FLAG_ROUTING_MODE, raising=False)
    monkeypatch.delenv(FLAG_SHADOW_ROUTING, raising=False)
    calls = adapter_spy()

    data = _post().json()

    assert data["provider_used"] == "gemini"
    assert data["audit"]["routing_mode"] == RoutingMode.LEGACY.value
    assert data["audit"]["real_provider_attempt_count"] == 1
    assert calls == [("gemini", settings.gemini_model)]


def test_old_shadow_flag_maps_to_shadow_without_affecting_execution(
    registry, all_configured, monkeypatch, adapter_spy
):
    monkeypatch.delenv(FLAG_ROUTING_MODE, raising=False)
    monkeypatch.setenv(FLAG_SHADOW_ROUTING, "true")
    calls = adapter_spy()

    data = _post().json()

    assert data["provider_used"] == "gemini"
    assert data["audit"]["routing_mode"] == RoutingMode.SHADOW.value
    assert data["audit"]["shadow_enabled"] is True
    assert calls == [("gemini", settings.gemini_model)]


def test_invalid_mode_rolls_back_to_legacy_fail_safe(
    registry, all_configured, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_ROUTING_MODE, "invented-by-consumer")
    calls = adapter_spy()

    data = _post().json()

    assert data["audit"]["routing_mode"] == RoutingMode.LEGACY.value
    assert data["audit"]["routing_configuration_valid"] is False
    assert data["audit"]["routing_configuration_reason"]
    assert calls == [("gemini", settings.gemini_model)]


def test_enforced_uses_policy_decision_and_calls_exactly_one_adapter(
    registry, all_configured, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    calls = adapter_spy()

    data = _post().json()

    assert data["provider_used"] == "gemini"
    assert data["model"] == settings.gemini_model
    assert data["audit"]["routing_selected_provider"] == "gemini"
    assert data["audit"]["routing_selected_model"] == settings.gemini_model
    assert data["audit"]["real_provider_attempt_count"] == 1
    assert calls == [("gemini", settings.gemini_model)]
    assert calls[0][1] is not None


def test_enforced_failure_uses_mock_and_never_calls_second_provider(
    registry, all_configured, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    calls = adapter_spy({"gemini"})

    data = _post().json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert data["audit"]["real_provider_attempt_count"] == 1
    assert calls == [("gemini", settings.gemini_model)]


def test_payload_cannot_control_routing_mode(
    registry, all_configured, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.LEGACY.value)
    calls = adapter_spy()

    data = _post(
        metadata={"routing_mode": "enforced", "shadow": True},
        context={"provider_routing_mode": "enforced"},
    ).json()

    assert "routing_mode" not in ChatRequest.model_fields
    assert data["audit"]["routing_mode"] == RoutingMode.LEGACY.value
    assert calls == [("gemini", settings.gemini_model)]


def test_ambiguous_identity_has_no_real_candidate(all_configured, monkeypatch):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)

    decision = shadow_routing_service.evaluate(
        caller=_context(strength=IdentityStrength.AMBIGUOUS),
        identity_project_id="shared_or_unknown",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    assert decision.selected_provider is None
    assert decision.candidates_considered[0].elimination_reason is (
        EliminationReason.AMBIGUOUS_IDENTITY
    )


def test_provider_configured_but_not_authorized_for_auto_is_eliminated(
    all_configured, monkeypatch
):
    specs = {
        provider_id: dict(spec)
        for provider_id, spec in provider_catalog_module._STATIC_SPECS.items()
    }
    specs["gemini"]["authorized_for_auto"] = False
    monkeypatch.setattr(provider_catalog_module, "_STATIC_SPECS", specs)
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)

    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    assert decision.selected_provider is None
    assert decision.candidates_considered[0].elimination_reason is (
        EliminationReason.NOT_AUTHORIZED
    )


def test_non_homologated_model_and_incompatible_task_are_eliminated(
    all_configured, monkeypatch
):
    entries = tuple(
        entry.model_copy(update={"homologated": False, "authorized": False})
        if entry.provider_id == "gemini"
        else entry
        for entry in provider_catalog_module._MODEL_CATALOG
    )
    monkeypatch.setattr(provider_catalog_module, "_MODEL_CATALOG", entries)
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)

    non_homologated = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    assert non_homologated.candidates_considered[0].elimination_reason is (
        EliminationReason.MODEL_NOT_HOMOLOGATED
    )

    entries = tuple(
        entry.model_copy(
            update={
                "homologated": True,
                "authorized": True,
                "excluded_tasks": ("assistant_chat",),
            }
        )
        if entry.provider_id == "gemini"
        else entry
        for entry in provider_catalog_module._MODEL_CATALOG
    )
    monkeypatch.setattr(provider_catalog_module, "_MODEL_CATALOG", entries)
    incompatible = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    assert incompatible.candidates_considered[0].elimination_reason is (
        EliminationReason.MODEL_INCOMPATIBLE
    )


def test_shadow_and_enforced_calculate_identical_first_candidate(
    all_configured, monkeypatch
):
    kwargs = {
        "caller": _context(),
        "identity_project_id": "finguard",
        "context_project_id": "finguard",
        "task_type": "assistant_chat",
        "allow_real_provider": True,
    }
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.SHADOW.value)
    shadow = shadow_routing_service.evaluate(**kwargs)
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    enforced = shadow_routing_service.evaluate(**kwargs)

    assert shadow.selected_provider == enforced.selected_provider == "gemini"
    assert shadow.selected_model == enforced.selected_model == settings.gemini_model
    assert _candidate_signature(shadow) == _candidate_signature(enforced)


def test_explicit_technical_selection_bypasses_automatic_ranking(
    registry, all_configured, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    calls = adapter_spy()

    data = _post(
        TOOL_KEY,
        provider="gemini",
        origin_system="pedrocore",
    ).json()

    assert data["provider_used"] == "gemini"
    assert data["audit"]["provider_selection_mode"] == "explicit"
    assert calls == [("gemini", settings.gemini_model)]


def test_finguard_contract_is_unchanged_and_routing_stays_internal(
    registry, all_configured, monkeypatch, adapter_spy
):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    adapter_spy()

    data = _post().json()
    response = OrchestrateResponse.model_validate(data)

    assert response.answer
    assert response.provider_used == "gemini"
    assert "routing_mode" not in OrchestrateResponse.model_fields
    assert "routing_candidates" not in OrchestrateResponse.model_fields


def test_local_trusted_remains_restricted_in_production(
    all_configured, monkeypatch
):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)

    decision = shadow_routing_service.evaluate(
        caller=_context(
            strength=IdentityStrength.LOCAL_TRUSTED,
            environment="production",
        ),
        identity_project_id="pedrocore",
        context_project_id="pedrocore",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    assert decision.selected_provider is None
    assert decision.candidates_considered[0].elimination_reason is (
        EliminationReason.NOT_AUTHORIZED
    )


def test_only_gemini_is_homologated_for_real_automatic_routing():
    homologated = [
        definition.provider_id
        for definition in provider_catalog_module.provider_catalog_service.definitions()
        if definition.is_real_provider
        and definition.is_approved_for_production
        and definition.authorized_for_auto
    ]

    assert homologated == ["gemini"]
