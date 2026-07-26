"""Política de roteamento em shadow mode (Etapa 4).

Prova que a decisão planejada é determinística, sanitizada e **sem efeito
algum** sobre a execução real: com shadow ligado ou desligado, o provider, o
modelo, a quantidade de chamadas e a resposta pública são idênticos.

Nenhum teste usa rede, chave real ou smoke real; o spy cobre todos os adapters.
"""

import json

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
from app.modules.orchestration.schemas import AssistantResponsePayload, OrchestrateResponse
from app.modules.orchestration.service import AUTO_REAL_PROVIDER_CANDIDATES
from app.modules.providers.base import ProviderExecutionError, ProviderResponse
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.openai_provider import OpenAIProvider
from app.modules.shadow_routing.schemas import POLICY_VERSION, EliminationReason
from app.modules.shadow_routing.service import FLAG_SHADOW_ROUTING, shadow_routing_service

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FAKE_PROVIDER_KEY = "chave-provider-sintetica-nunca-real"

FINGUARD_KEY = "finguard-consumidor-shadow-sintetica"
TOOL_KEY = "pedrocore-tecnica-shadow-sintetica"

REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-app",
            "api_key": FINGUARD_KEY,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
        },
        {
            "credential_id": "pedrocore-tool",
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
def shadow_on(monkeypatch):
    monkeypatch.setenv(FLAG_SHADOW_ROUTING, "true")


@pytest.fixture
def shadow_off(monkeypatch):
    monkeypatch.delenv(FLAG_SHADOW_ROUTING, raising=False)


@pytest.fixture
def adapter_spy(monkeypatch):
    calls: list[tuple[str, str | None]] = []

    def install(failing: set[str] | None = None):
        failing = failing or set()

        def make(name: str):
            async def stub(self, message, mode, model=None, system_prompt=None):
                calls.append((name, model))
                if name in failing:
                    raise ProviderExecutionError(f"Falha simulada de {name}.")
                return ProviderResponse(
                    answer=f"Resposta stubada de {name}.",
                    provider=name,
                    model=model or f"{name}-stub-v1",
                )

            return stub

        for cls in REAL_PROVIDER_CLASSES:
            monkeypatch.setattr(cls, "generate_response", make(cls.name))
        return calls

    install.calls = calls
    return install


def _post(credential: str | None, **overrides):
    payload = {
        "message": "Pergunta segura de shadow mode.",
        "provider": "auto",
        "task_type": "assistant_chat",
        "origin_system": "finguard",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    headers = {AUTH_HEADER: credential} if credential else {}
    return client.post("/api/orchestrate", json=payload, headers=headers)


def _context(role=CallerRole.TECHNICAL_TOOL, strength=IdentityStrength.REGISTERED):
    from app.modules.caller_identity.schemas import AuthenticatedCallerContext

    if strength is IdentityStrength.AMBIGUOUS:
        return AuthenticatedCallerContext(
            credential_id="shadow-ambiguo",
            caller_role=CallerRole.COMMON_CONSUMER,
            environment="development",
            identity_strength=IdentityStrength.AMBIGUOUS,
            project_id="shared_or_unknown",
        )
    return AuthenticatedCallerContext(
        credential_id="shadow-registrado",
        caller_role=role,
        environment="development",
        identity_strength=strength,
        project_id="finguard",
        allowed_origins=("finguard",),
    )


# ---------------------------------------------------------------------------
# Efeito nulo sobre a execução real
# ---------------------------------------------------------------------------
def test_shadow_disabled_does_not_change_behavior(
    registry, all_configured, shadow_off, adapter_spy
):
    calls = adapter_spy()

    data = _post(FINGUARD_KEY).json()

    assert data["provider_used"] == "gemini"
    assert data["audit"]["shadow_enabled"] is False
    assert data["audit"]["shadow_selected_provider"] is None
    assert calls == [("gemini", settings.gemini_model)]


def test_shadow_enabled_changes_nothing_in_the_real_execution(
    registry, all_configured, monkeypatch, adapter_spy
):
    """Mesma entrada e mesmos stubs: shadow ligado == shadow desligado."""
    calls = adapter_spy()

    monkeypatch.delenv(FLAG_SHADOW_ROUTING, raising=False)
    without = _post(FINGUARD_KEY).json()
    calls_without = list(calls)

    calls.clear()
    monkeypatch.setenv(FLAG_SHADOW_ROUTING, "true")
    with_shadow = _post(FINGUARD_KEY).json()
    calls_with = list(calls)

    assert without["provider_used"] == with_shadow["provider_used"]
    assert without["model"] == with_shadow["model"]
    assert without["answer"] == with_shadow["answer"]
    assert without["status"] == with_shadow["status"]
    assert without["fallback_used"] == with_shadow["fallback_used"]
    assert without["release_gate"] == with_shadow["release_gate"]
    assert without["warning_codes"] == with_shadow["warning_codes"]
    assert calls_without == calls_with == [("gemini", settings.gemini_model)]


def test_shadow_never_calls_an_adapter_even_when_it_would_prefer_another_provider(
    registry, all_configured, shadow_on, adapter_spy
):
    calls = adapter_spy()

    data = _post(FINGUARD_KEY).json()
    audit = data["audit"]

    # Uma única chamada real, ao provider do roteamento atual.
    assert calls == [("gemini", settings.gemini_model)]
    assert audit["shadow_enabled"] is True
    assert "claude" not in [call[0] for call in calls]
    assert "openai" not in [call[0] for call in calls]


def test_shadow_does_not_start_a_real_fallback(
    registry, all_configured, shadow_on, adapter_spy
):
    calls = adapter_spy(failing={"gemini"})

    data = _post(FINGUARD_KEY).json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    # Gemini falhou: continua indo para Mock, nunca para um segundo provider.
    assert [call[0] for call in calls] == ["gemini"]


def test_at_most_one_real_call_per_request(registry, all_configured, shadow_on, adapter_spy):
    calls = adapter_spy(failing={"gemini"})

    for provider in ("auto", "mock", "local_qa"):
        calls.clear()
        _post(FINGUARD_KEY, provider=provider, allow_real_provider=False)
        assert len(calls) <= 1, provider

    calls.clear()
    _post(FINGUARD_KEY, provider="auto")
    assert len(calls) <= 1


def test_auto_remains_gemini_only_with_shadow_enabled(
    registry, all_configured, shadow_on, adapter_spy
):
    calls = adapter_spy()

    data = _post(FINGUARD_KEY).json()

    assert AUTO_REAL_PROVIDER_CANDIDATES == ("gemini",)
    assert data["provider_used"] == "gemini"
    assert calls == [("gemini", settings.gemini_model)]


# ---------------------------------------------------------------------------
# Filtros eliminatórios
# ---------------------------------------------------------------------------
def test_unconfigured_candidates_are_eliminated(monkeypatch, shadow_on):
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")

    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )
    reasons = {
        item.provider_id: item.elimination_reason for item in decision.candidates_eliminated
    }

    assert reasons["claude"] is EliminationReason.NOT_CONFIGURED
    assert reasons["openai"] is EliminationReason.NOT_CONFIGURED
    assert decision.selected_provider == "gemini"


def test_configured_but_non_homologated_candidates_are_eliminated(
    monkeypatch, all_configured, shadow_on
):
    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )
    reasons = {
        item.provider_id: item.elimination_reason for item in decision.candidates_eliminated
    }

    # Chave presente não torna elegível: o motivo correto é a homologação.
    assert reasons["claude"] is EliminationReason.NOT_HOMOLOGATED
    assert reasons["openai"] is EliminationReason.NOT_HOMOLOGATED
    assert decision.selected_provider == "gemini"


def test_unauthorized_project_eliminates_every_real_candidate(all_configured, shadow_on):
    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="projeto-sem-autorizacao",
        context_project_id="projeto-sem-autorizacao",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    assert decision.selected_provider is None
    assert decision.candidates_eliminated
    assert any(
        item.elimination_reason
        in {EliminationReason.NOT_AUTHORIZED, EliminationReason.NOT_HOMOLOGATED}
        for item in decision.candidates_eliminated
    )


def test_ambiguous_identity_produces_zero_eligible_real_candidates(
    all_configured, shadow_on
):
    decision = shadow_routing_service.evaluate(
        caller=_context(strength=IdentityStrength.AMBIGUOUS),
        identity_project_id="shared_or_unknown",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    assert decision.selected_provider is None
    assert decision.selected_model is None
    assert all(item.eliminated for item in decision.candidates_considered)
    assert (
        decision.candidates_considered[0].elimination_reason
        is EliminationReason.AMBIGUOUS_IDENTITY
    )


def test_safe_mode_eliminates_real_candidates(all_configured, shadow_on):
    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=False,
    )
    reasons = {
        item.provider_id: item.elimination_reason for item in decision.candidates_eliminated
    }

    assert decision.selected_provider is None
    assert reasons["gemini"] is EliminationReason.SAFE_MODE_BLOCKED


def test_project_policy_blocked_eliminates_candidates(all_configured, shadow_on):
    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
        policy_allowed=False,
    )

    assert decision.selected_provider is None
    assert any(
        item.elimination_reason is EliminationReason.PROJECT_POLICY_BLOCKED
        for item in decision.candidates_eliminated
    )


def test_task_incompatible_candidate_is_eliminated(all_configured, shadow_on, monkeypatch):
    """Task fora da compatibilidade do provider elimina o candidato."""
    from app.modules.provider_catalog.service import _STATIC_SPECS

    monkeypatch.setitem(
        _STATIC_SPECS["gemini"], "excluded_tasks", ("assistant_chat",)
    )

    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )
    reasons = {
        item.provider_id: item.elimination_reason for item in decision.candidates_eliminated
    }

    assert reasons["gemini"] is EliminationReason.TASK_INCOMPATIBLE
    assert decision.selected_provider is None


def test_model_incompatible_candidate_is_eliminated(all_configured, shadow_on, monkeypatch):
    monkeypatch.setattr(GeminiProvider, "default_model", "")

    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )
    reasons = {
        item.provider_id: item.elimination_reason for item in decision.candidates_eliminated
    }

    assert reasons["gemini"] is EliminationReason.MODEL_INCOMPATIBLE
    assert decision.selected_provider is None


# ---------------------------------------------------------------------------
# Determinismo
# ---------------------------------------------------------------------------
def test_static_priority_is_declared_and_deterministic():
    assert shadow_routing_service.priority_for("finguard", "assistant_chat") == (
        "gemini",
        "claude",
        "openai",
    )
    assert shadow_routing_service.priority_for("finguard", "task-desconhecida") == (
        "gemini",
        "claude",
        "openai",
    )
    assert shadow_routing_service.priority_for("projeto-novo", "qualquer") == (
        "gemini",
        "claude",
        "openai",
    )


def test_same_input_produces_the_same_decision(all_configured, shadow_on):
    kwargs = {
        "caller": _context(),
        "identity_project_id": "finguard",
        "context_project_id": "finguard",
        "task_type": "assistant_chat",
        "allow_real_provider": True,
    }

    first = shadow_routing_service.evaluate(**kwargs)
    second = shadow_routing_service.evaluate(**kwargs)
    third = shadow_routing_service.evaluate(**kwargs)

    assert first.model_dump() == second.model_dump() == third.model_dump()


def test_candidate_order_does_not_depend_on_dict_or_set_iteration(
    all_configured, shadow_on
):
    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    considered = [item.provider_id for item in decision.candidates_considered]
    priorities = [item.priority for item in decision.candidates_considered]

    assert considered == ["gemini", "claude", "openai"]
    assert priorities == sorted(priorities) == [0, 1, 2]


def test_tie_break_selects_the_first_surviving_candidate_in_static_order(
    monkeypatch, all_configured, shadow_on
):
    """Sem Gemini configurado, nenhum outro é promovido artificialmente."""
    monkeypatch.setattr(settings, "gemini_api_key", "")

    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    assert decision.selected_provider is None
    assert decision.candidates_considered[0].provider_id == "gemini"


# ---------------------------------------------------------------------------
# Comparação com o real, ativação e sanitização
# ---------------------------------------------------------------------------
def test_would_differ_is_computed_without_execution(
    registry, all_configured, shadow_on, adapter_spy
):
    calls = adapter_spy()

    data = _post(FINGUARD_KEY).json()
    audit = data["audit"]

    assert audit["shadow_selected_provider"] == "gemini"
    assert audit["shadow_selected_model"] == settings.gemini_model
    assert audit["shadow_would_differ"] is False
    assert audit["shadow_policy_version"] == POLICY_VERSION
    # Uma única chamada: nada foi executado para calcular a comparação.
    assert calls == [("gemini", settings.gemini_model)]


def test_would_differ_is_true_when_planned_and_effective_differ(
    registry, all_configured, shadow_on, adapter_spy
):
    calls = adapter_spy(failing={"gemini"})

    data = _post(FINGUARD_KEY).json()
    audit = data["audit"]

    assert data["provider_used"] == "mock"
    assert audit["shadow_selected_provider"] == "gemini"
    assert audit["shadow_would_differ"] is True
    assert [call[0] for call in calls] == ["gemini"]


def test_consumer_cannot_enable_shadow_through_the_payload(
    registry, all_configured, shadow_off, adapter_spy
):
    adapter_spy()

    data = _post(
        FINGUARD_KEY,
        metadata={"shadow": True, "shadow_mode": "on"},
        context={"shadow_routing_enabled": True},
    ).json()

    assert data["audit"]["shadow_enabled"] is False
    assert shadow_routing_service.enabled() is False


def test_shadow_flag_is_off_by_default(shadow_off):
    assert shadow_routing_service.enabled() is False


def test_shadow_decision_carries_no_secret(registry, all_configured, shadow_on, adapter_spy):
    adapter_spy()

    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )
    dumped = json.dumps(decision.model_dump(), ensure_ascii=False)

    assert FAKE_PROVIDER_KEY not in dumped
    assert FINGUARD_KEY not in dumped
    for fragment in ("api_key", "apikey", "secret", "password", "senha", "token"):
        assert fragment not in dumped.lower()


def test_binding_from_stage_three_is_respected_by_the_shadow_policy(
    all_configured, shadow_on
):
    decision = shadow_routing_service.evaluate(
        caller=_context(),
        identity_project_id="finguard",
        context_project_id="finguard",
        task_type="assistant_chat",
        allow_real_provider=True,
    )

    assert decision.selected_provider == "gemini"
    # Modelo planejado vem do binding/catálogo, nunca de um payload.
    assert decision.selected_model == settings.gemini_model


def test_public_contract_has_no_shadow_field():
    orchestrate_fields = set(OrchestrateResponse.model_fields)
    frontend_fields = set(AssistantResponsePayload.model_fields)

    for forbidden in (
        "shadow_decision",
        "shadow_routing",
        "shadow_enabled",
        "candidates_considered",
    ):
        assert forbidden not in orchestrate_fields
        assert forbidden not in frontend_fields
    assert {"answer", "suggestions", "disclaimer"} <= frontend_fields


def test_local_trusted_and_ambiguous_restrictions_still_hold(monkeypatch, all_configured):
    """Regressão de segurança do modo local (missão §14)."""
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)

    local = caller_identity_service.default_context()
    assert local.identity_strength is IdentityStrength.LOCAL_TRUSTED

    from app.modules.provider_authorization.service import provider_authorization_service

    # local_trusted não assume FinGuard.
    finguard = provider_authorization_service.evaluate(
        identity_strength=IdentityStrength.LOCAL_TRUSTED,
        project_id="finguard",
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="development",
        provider_id="gemini",
    )
    assert finguard.denied is True

    # local_trusted não vale em produção.
    production = provider_authorization_service.evaluate(
        identity_strength=IdentityStrength.LOCAL_TRUSTED,
        project_id="pedrocore",
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="production",
        provider_id="gemini",
    )
    assert production.denied is True

    # ambiguous nunca autoriza provider real.
    ambiguous = provider_authorization_service.evaluate(
        identity_strength=IdentityStrength.AMBIGUOUS,
        project_id="finguard",
        caller_role=CallerRole.COMMON_CONSUMER,
        environment="development",
        provider_id="gemini",
    )
    assert ambiguous.denied is True

    # somente registered estabelece identidade de projeto consumidor.
    registered = provider_authorization_service.evaluate(
        identity_strength=IdentityStrength.REGISTERED,
        project_id="finguard",
        caller_role=CallerRole.COMMON_CONSUMER,
        environment="development",
        provider_id="gemini",
    )
    assert registered.allowed is True
