"""Provider/model binding (MULTI-PROVIDER-SAFE-EVOLUTION, Etapa 3).

Prova que provider e modelo são validados como UMA unidade: combinação
incompatível é bloqueada antes de qualquer adapter, consumidor comum não
define modelo, `provider=auto` continua Gemini-only com modelo derivado
internamente, e Mock/`local_qa`/`local_model` têm binding próprio.

Nenhum teste usa rede, chave real ou smoke real.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.schemas import CallerRole
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.contracts import codes
from app.modules.orchestration.schemas import AssistantResponsePayload
from app.modules.orchestration.service import (
    AUTO_REAL_PROVIDER_CANDIDATES,
    LOCAL_PROVIDER_MODEL,
)
from app.modules.provider_binding.schemas import BindingValidation, ModelSource
from app.modules.provider_binding.service import provider_binding_service
from app.modules.provider_catalog import service as provider_catalog_module
from app.modules.provider_catalog.schemas import ModelDefinition
from app.modules.provider_catalog.service import provider_catalog_service
from app.modules.providers.base import ProviderExecutionError, ProviderResponse
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.openai_provider import OpenAIProvider

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FAKE_PROVIDER_KEY = "chave-provider-sintetica-nunca-real"

PEDROCORE_TOOL_KEY = "pedrocore-tecnica-sintetica"
FINGUARD_CONSUMER_KEY = "finguard-consumidor-sintetica"

REGISTRY = json.dumps(
    [
        {
            "credential_id": "pedrocore-tool",
            "api_key": PEDROCORE_TOOL_KEY,
            "project_id": "pedrocore",
            "role": "technical_tool",
            "environment": "development",
            "allowed_origins": ["pedrocore"],
        },
        {
            "credential_id": "finguard-app",
            "api_key": FINGUARD_CONSUMER_KEY,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
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
    """Spy em todos os adapters reais: nenhuma chamada externa é possível."""
    calls: list[tuple[str, str | None]] = []

    def install(failing: set[str] | None = None):
        failing = failing or set()

        def make(name: str):
            async def stub(self, message, mode, model=None, system_prompt=None, **kwargs):
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
        "message": "Pergunta segura de binding.",
        "provider": "gemini",
        "task_type": "assistant_chat",
        "origin_system": "pedrocore",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    headers = {AUTH_HEADER: credential} if credential else {}
    return client.post("/api/orchestrate", json=payload, headers=headers)


# ---------------------------------------------------------------------------
# Catálogo como fonte única de verdade de modelos
# ---------------------------------------------------------------------------
def test_each_known_model_belongs_to_exactly_one_provider(all_configured):
    owners: dict[str, list[str]] = {}
    for model in provider_catalog_service.models():
        owners.setdefault(model.model_id, []).append(model.provider_id)

    for model_id, providers in owners.items():
        assert len(providers) == 1, (model_id, providers)


def test_arbitrary_adapter_default_does_not_create_or_homologate_model(
    monkeypatch, registry, all_configured, adapter_spy
):
    calls = adapter_spy()
    arbitrary = "gemini-modelo-arbitrario-nao-homologado"
    before = provider_catalog_service.models_for("gemini")
    monkeypatch.setattr(GeminiProvider, "default_model", arbitrary)

    after = provider_catalog_service.models_for("gemini")
    configured_binding = provider_binding_service.resolve(
        requested_provider="gemini",
        requested_model=None,
        selection_mode="explicit",
        caller_role=CallerRole.TECHNICAL_TOOL,
        task_type="assistant_chat",
    )
    configured = _post(PEDROCORE_TOOL_KEY, provider="gemini").json()
    explicit = _post(
        PEDROCORE_TOOL_KEY,
        provider="gemini",
        model=arbitrary,
    ).json()

    assert after == before
    assert provider_catalog_service.find_model(arbitrary) is None
    assert configured_binding.invalid is True
    assert configured_binding.error_code == codes.MODEL_DEFAULT_UNAVAILABLE
    assert configured["status"] == "blocked"
    assert configured["error_code"] == codes.MODEL_DEFAULT_UNAVAILABLE
    assert explicit["status"] == "blocked"
    assert explicit["error_code"] == codes.MODEL_UNKNOWN
    assert calls == []


def test_provider_homologation_does_not_homologate_its_model(
    monkeypatch, registry, all_configured, adapter_spy
):
    calls = adapter_spy()
    entries = tuple(
        entry.model_copy(update={"homologated": False, "authorized": False})
        if entry.provider_id == "gemini"
        else entry
        for entry in provider_catalog_module._MODEL_CATALOG
    )
    monkeypatch.setattr(provider_catalog_module, "_MODEL_CATALOG", entries)

    assert provider_catalog_service.get("gemini").is_approved_for_production is True
    assert provider_catalog_service.default_model_for("gemini").homologated is False

    data = _post(
        PEDROCORE_TOOL_KEY,
        provider="gemini",
        model=settings.gemini_model,
    ).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.MODEL_NOT_AUTHORIZED
    assert calls == []


def test_catalog_position_does_not_determine_model_homologation():
    first = ModelDefinition(
        provider_id="provider-de-teste",
        model_id="modelo-sintetico-nao-produtivo",
        registered=True,
        implemented=True,
        homologated=False,
        authorized=False,
        default_for_provider=False,
    )

    assert (first,)[0].homologated is False


def test_every_provider_default_model_comes_from_the_catalog(all_configured):
    for provider_id in ("gemini", "claude", "openai", "mock", "local_qa"):
        default = provider_catalog_service.default_model_for(provider_id)
        assert default is not None, provider_id
        assert default.provider_id == provider_id
        assert default.default_for_provider is True

    assert provider_catalog_service.default_model_for("local_qa").model_id == (
        LOCAL_PROVIDER_MODEL
    )


def test_configured_model_is_not_automatically_homologated_or_authorized(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", FAKE_PROVIDER_KEY)

    claude_model = provider_catalog_service.default_model_for("claude")

    assert claude_model is not None
    assert provider_catalog_service.get("claude").configured is True
    # Provider não homologado => modelo não homologado nem autorizado.
    assert claude_model.homologated is False


# ---------------------------------------------------------------------------
# Combinações incompatíveis
# ---------------------------------------------------------------------------
def test_gemini_with_claude_model_is_blocked(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="gemini", model=settings.anthropic_model).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.MODEL_PROVIDER_MISMATCH
    assert data["provider_used"] == "none"
    assert calls == []


def test_claude_with_openai_model_is_blocked(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="claude", model=settings.openai_model).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.MODEL_PROVIDER_MISMATCH
    assert calls == []


def test_unknown_model_is_blocked(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="gemini", model="modelo-que-nao-existe").json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.MODEL_UNKNOWN
    assert calls == []


def test_unknown_provider_never_reaches_an_adapter(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="provider_inexistente").json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert calls == []


def test_invalid_binding_never_touches_the_adapter(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    for provider, model in (
        ("gemini", settings.anthropic_model),
        ("gemini", settings.openai_model),
        ("claude", settings.gemini_model),
        ("openai", settings.gemini_model),
        ("gemini", "modelo-inventado"),
    ):
        data = _post(PEDROCORE_TOOL_KEY, provider=provider, model=model).json()
        assert data["status"] == "blocked", (provider, model)
        assert data["provider_used"] == "none", (provider, model)

    assert calls == []


# ---------------------------------------------------------------------------
# Consumidor comum
# ---------------------------------------------------------------------------
def test_common_consumer_cannot_send_model(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    data = _post(
        FINGUARD_CONSUMER_KEY,
        provider="auto",
        origin_system="finguard",
        model=settings.gemini_model,
    ).json()

    assert data["status"] == "blocked"
    assert data["error_code"] in {
        codes.CALLER_MODEL_SELECTION_NOT_ALLOWED,
        codes.MODEL_NOT_ALLOWED_FOR_CALLER,
    }
    assert calls == []


def test_common_consumer_cannot_use_model_to_pick_provider(
    registry, all_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(
        FINGUARD_CONSUMER_KEY,
        provider="auto",
        origin_system="finguard",
        model=settings.anthropic_model,
    ).json()

    assert data["status"] == "blocked"
    assert "claude" not in [call[0] for call in calls]
    assert calls == []


def test_finguard_normal_flow_gets_internally_derived_gemini_model(
    registry, all_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(FINGUARD_CONSUMER_KEY, provider="auto", origin_system="finguard").json()

    assert data["provider_used"] == "gemini"
    assert data["model"] == settings.gemini_model
    assert data["audit"]["model_requested"] is None
    assert data["audit"]["model_source"] == ModelSource.PROVIDER_DEFAULT.value
    assert calls == [("gemini", settings.gemini_model)]


# ---------------------------------------------------------------------------
# Ferramenta técnica
# ---------------------------------------------------------------------------
def test_technical_tool_can_select_a_valid_model_of_the_authorized_provider(
    registry, all_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="gemini", model=settings.gemini_model).json()

    assert data["provider_used"] == "gemini"
    assert data["model"] == settings.gemini_model
    assert data["audit"]["model_source"] == ModelSource.EXPLICIT_TECHNICAL.value
    assert calls == [("gemini", settings.gemini_model)]


def test_technical_tool_with_incompatible_model_is_blocked_before_adapter(
    registry, all_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="gemini", model=settings.anthropic_model).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.MODEL_PROVIDER_MISMATCH
    # Sem fallback silencioso para o default: quem pediu explicitamente é rejeitado.
    assert data["model"] == "none"
    assert calls == []


def test_non_homologated_model_is_not_authorized_even_when_configured(
    registry, all_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="claude", model=settings.anthropic_model).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.MODEL_NOT_AUTHORIZED
    assert calls == []


# ---------------------------------------------------------------------------
# Modo automático
# ---------------------------------------------------------------------------
def test_auto_rejects_model_as_indirect_provider_selection(
    registry, all_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="auto", model=settings.anthropic_model).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.MODEL_NOT_ALLOWED_IN_AUTO
    assert calls == []


def test_auto_remains_gemini_only_with_internal_model(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="auto").json()

    assert AUTO_REAL_PROVIDER_CANDIDATES == ("gemini",)
    assert data["provider_used"] == "gemini"
    assert calls == [("gemini", settings.gemini_model)]


def test_only_claude_configured_with_auto_still_results_in_mock(
    registry, monkeypatch, adapter_spy
):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "anthropic_api_key", FAKE_PROVIDER_KEY)
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="auto").json()

    assert data["provider_used"] == "mock"
    assert data["error_code"] == codes.PROVIDER_REAL_UNAVAILABLE
    assert calls == []


def test_gemini_failure_still_falls_back_to_mock_never_to_claude(
    registry, all_configured, adapter_spy
):
    calls = adapter_spy(failing={"gemini"})

    data = _post(PEDROCORE_TOOL_KEY, provider="auto").json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert [call[0] for call in calls] == ["gemini"]


def test_no_request_calls_two_real_adapters(registry, all_configured, adapter_spy):
    calls = adapter_spy(failing={"gemini"})

    for provider, model in (
        ("auto", None),
        ("gemini", settings.gemini_model),
        ("gemini", None),
        ("mock", None),
        ("local_qa", None),
    ):
        calls.clear()
        overrides = {"provider": provider}
        if model:
            overrides["model"] = model
        _post(PEDROCORE_TOOL_KEY, **overrides)
        assert len(calls) <= 1, (provider, model, calls)
        assert all(bound_model is not None for _, bound_model in calls)


# ---------------------------------------------------------------------------
# Mock, local_qa e local_model
# ---------------------------------------------------------------------------
def test_mock_uses_its_own_safe_binding(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="mock", allow_real_provider=False).json()

    assert data["provider_used"] == "mock"
    assert data["model"] == "mock-v1"
    assert data["audit"]["model_selected"] == "mock-v1"
    assert data["audit"]["model_source"] == ModelSource.LOCAL_FIXED.value
    assert calls == []


def test_local_qa_uses_its_own_binding(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    data = _post(
        PEDROCORE_TOOL_KEY,
        provider="local_qa",
        task_type="qa_report_analysis",
        allow_real_provider=False,
        artifacts=[{"type": "qa_report", "content": "120 passed, 0 failed."}],
    ).json()

    assert data["provider_used"] == "local_qa"
    assert data["model"] == LOCAL_PROVIDER_MODEL
    assert data["audit"]["model_selected"] == LOCAL_PROVIDER_MODEL
    assert calls == []


def test_local_providers_reject_external_model_names(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    for provider in ("mock", "local_qa", "local_model"):
        data = _post(
            PEDROCORE_TOOL_KEY,
            provider=provider,
            model=settings.gemini_model,
            allow_real_provider=False,
        ).json()
        assert data["status"] == "blocked", provider
        assert data["error_code"] == codes.MODEL_PROVIDER_MISMATCH, provider

    assert calls == []


def test_task_incompatible_model_is_blocked(registry, all_configured, adapter_spy):
    calls = adapter_spy()

    data = _post(
        PEDROCORE_TOOL_KEY,
        provider="mock",
        model="mock-v1",
        task_type="release_gate_review",
        allow_real_provider=False,
        artifacts=[{"type": "qa_report", "content": "0 failed."}],
    ).json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.MODEL_TASK_INCOMPATIBLE
    assert calls == []


# ---------------------------------------------------------------------------
# Resolução direta do binding (unitário)
# ---------------------------------------------------------------------------
def test_binding_resolution_is_deterministic_and_typed(all_configured):
    selected = provider_binding_service.resolve(
        requested_provider="gemini",
        requested_model=None,
        selection_mode="explicit",
        caller_role=CallerRole.TECHNICAL_TOOL,
        task_type="assistant_chat",
    )

    assert selected.validation_result is BindingValidation.VALID
    assert selected.provider_id == "gemini"
    assert selected.model_id == settings.gemini_model
    assert selected.binding is not None
    assert selected.binding.adapter_id == "GeminiProvider"
    assert selected.binding.default_for_provider is True

    invalid = provider_binding_service.resolve(
        requested_provider="gemini",
        requested_model=settings.anthropic_model,
        selection_mode="explicit",
        caller_role=CallerRole.TECHNICAL_TOOL,
        task_type="assistant_chat",
    )
    assert invalid.invalid is True
    assert invalid.error_code == codes.MODEL_PROVIDER_MISMATCH
    assert invalid.model_id is None


def test_explicit_provider_without_valid_default_blocks_before_adapter(
    monkeypatch, registry, adapter_spy
):
    """Seleção explícita sem default válido bloqueia antes do adapter."""
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)
    monkeypatch.setattr(GeminiProvider, "default_model", "")
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="gemini").json()

    assert data["status"] == "blocked"
    assert data["provider_used"] == "none"
    assert data["error_code"] == codes.MODEL_DEFAULT_UNAVAILABLE
    assert calls == []


def test_auto_without_valid_default_uses_only_safe_mock(
    monkeypatch, registry, adapter_spy
):
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)
    monkeypatch.setattr(GeminiProvider, "default_model", "")
    calls = adapter_spy()

    data = _post(PEDROCORE_TOOL_KEY, provider="auto").json()

    assert data["status"] == "ok"
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert data["error_code"] == codes.MODEL_DEFAULT_UNAVAILABLE
    assert codes.MODEL_DEFAULT_UNAVAILABLE in data["warning_codes"]
    assert calls == []


# ---------------------------------------------------------------------------
# Auditoria, observabilidade e contrato público
# ---------------------------------------------------------------------------
def test_audit_distinguishes_requested_from_selected_model(
    registry, all_configured, adapter_spy
):
    adapter_spy()

    explicit = _post(PEDROCORE_TOOL_KEY, provider="gemini", model=settings.gemini_model).json()
    derived = _post(PEDROCORE_TOOL_KEY, provider="gemini").json()

    assert explicit["audit"]["model_requested"] == settings.gemini_model
    assert explicit["audit"]["model_selected"] == settings.gemini_model
    assert derived["audit"]["model_requested"] is None
    assert derived["audit"]["model_selected"] == settings.gemini_model


def test_shared_credential_still_cannot_reach_a_real_provider(
    monkeypatch, all_configured, adapter_spy
):
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, "chave-global-sintetica")
    calls = adapter_spy()

    data = _post("chave-global-sintetica", provider="auto", origin_system="finguard").json()

    assert data["provider_used"] == "mock"
    assert data["error_code"] == codes.CALLER_IDENTITY_AMBIGUOUS
    assert calls == []


def test_finguard_public_contract_has_no_binding_metadata():
    fields = set(AssistantResponsePayload.model_fields)

    assert {"answer", "suggestions", "disclaimer"} <= fields
    for forbidden in ("model_requested", "model_selected", "model_source", "binding"):
        assert forbidden not in fields
