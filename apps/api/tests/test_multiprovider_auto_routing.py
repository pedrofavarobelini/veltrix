"""MULTIPROVIDER-ORCHESTRATION-V1: `provider=auto` com mais de um homologado.

Prova que o conjunto de candidatos do automático vem do catálogo (fonte única)
e que um segundo provider homologado pode atender a Elyra sem nenhuma mudança
no contrato do consumer. Tudo é sintético: os adapters reais são substituídos
por fakes ou bloqueados pelo `real_provider_guard`; nenhuma chave real existe.

Claude/OpenAI/Grok/DeepSeek só são homologados DENTRO do escopo de cada teste;
o catálogo de produção continua com somente Gemini homologado.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.schemas import CallerRole, IdentityStrength
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.contracts import codes
from app.modules.elyra_textual.idempotency import elyra_idempotency_service
from app.modules.orchestration.service import (
    FLAG_REAL_FALLBACK_ENABLED,
    auto_real_provider_candidates,
)
from app.modules.provider_authorization import service as authorization_module
from app.modules.provider_catalog import service as catalog_module
from app.modules.provider_catalog.schemas import (
    HomologationStatus,
    ProviderCapability,
)
from app.modules.provider_catalog.service import provider_catalog_service
from app.modules.provider_health.schemas import FailureClassification
from app.modules.provider_health.service import (
    FLAG_CIRCUIT_ENABLED,
    provider_health_service,
)
from app.modules.providers.base import ProviderResponse
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.openai_provider import OpenAIProvider
from app.modules.shadow_routing import service as routing_module
from app.modules.shadow_routing.schemas import (
    POLICY_VERSION,
    EliminationReason,
    RoutingMode,
)
from app.modules.shadow_routing.service import FLAG_ROUTING_MODE
from tests.test_elyra_consumer_onboarding import _payload, _valid_output

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
ELYRA_KEY = "elyra-multiprovider-synthetic"
FINGUARD_KEY = "finguard-multiprovider-synthetic"
FAKE_PROVIDER_KEY = "multiprovider-synthetic-never-real"
ELYRA_TASK = "wellbeing_report_interpretation"

ADAPTERS = {
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
    "grok": GrokProvider,
}
KEY_SETTING = {
    "gemini": "gemini_api_key",
    "claude": "anthropic_api_key",
    "openai": "openai_api_key",
    "deepseek": "deepseek_api_key",
    "grok": "xai_api_key",
}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, real_provider_guard):
    """Isola estado e garante que só adapters explicitamente falsificados rodem."""
    elyra_idempotency_service.clear()
    provider_health_service.reset()
    monkeypatch.setenv(
        FLAG_CALLER_REGISTRY,
        json.dumps(
            [
                {
                    "credential_id": "elyra-multiprovider",
                    "api_key": ELYRA_KEY,
                    "project_id": "elyra",
                    "role": "common_consumer",
                    "environment": "development",
                    "allowed_origins": ["elyra"],
                },
                {
                    "credential_id": "finguard-multiprovider",
                    "api_key": FINGUARD_KEY,
                    "project_id": "finguard",
                    "role": "common_consumer",
                    "environment": "development",
                    "allowed_origins": ["finguard"],
                },
            ]
        ),
    )
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.ENFORCED.value)
    monkeypatch.delenv(FLAG_REAL_FALLBACK_ENABLED, raising=False)
    monkeypatch.delenv(FLAG_CIRCUIT_ENABLED, raising=False)
    # Nenhuma chave por padrão: cada teste configura explicitamente.
    for attribute in KEY_SETTING.values():
        monkeypatch.setattr(settings, attribute, "")
    yield real_provider_guard
    provider_health_service.reset()
    elyra_idempotency_service.clear()


def configure(monkeypatch, *providers: str) -> None:
    """Simula chave presente. Configurar NUNCA homologa nada."""
    for provider_id in providers:
        monkeypatch.setattr(settings, KEY_SETTING[provider_id], FAKE_PROVIDER_KEY)
    if {"deepseek", "grok"} & set(providers):
        monkeypatch.setattr(settings, "deepseek_base_url", "https://deepseek.invalid")
        monkeypatch.setattr(settings, "xai_base_url", "https://xai.invalid")


def homologate(
    monkeypatch,
    *providers: str,
    model_homologated: bool = True,
    authorize_projects: frozenset[str] = frozenset({"elyra", "finguard"}),
) -> None:
    """Homologação sintética no escopo do teste: catálogo + modelo + matriz."""
    specs = {provider_id: dict(spec) for provider_id, spec in catalog_module._STATIC_SPECS.items()}
    for provider_id in providers:
        specs[provider_id]["homologation"] = HomologationStatus.HOMOLOGATED_REAL
        specs[provider_id]["authorized_for_auto"] = True
    monkeypatch.setattr(catalog_module, "_STATIC_SPECS", specs)

    models = tuple(
        entry.model_copy(update={"homologated": model_homologated, "authorized": model_homologated})
        if entry.provider_id in providers
        else entry
        for entry in catalog_module._MODEL_CATALOG
    )
    monkeypatch.setattr(catalog_module, "_MODEL_CATALOG", models)

    if authorize_projects:
        rule = authorization_module.AuthorizationRule(
            identity_strengths=frozenset({IdentityStrength.REGISTERED}),
            project_ids=authorize_projects,
            caller_roles=frozenset({CallerRole.COMMON_CONSUMER}),
            environments=frozenset({"development"}),
            providers=frozenset(providers),
            notes="Somente teste sintético multiprovider.",
        )
        monkeypatch.setattr(authorization_module, "_RULES", (*authorization_module._RULES, rule))


def fake_adapters(monkeypatch, behavior: dict[str, object] | None = None):
    """Fakes que devolvem output Elyra válido; registram (provider, modelo)."""
    behavior = behavior or {}
    calls: list[tuple[str, str]] = []

    def make(provider_id: str):
        async def generate(self, message, mode, model=None, system_prompt=None, **kwargs):
            calls.append((provider_id, model))
            action = behavior.get(provider_id)
            if isinstance(action, Exception):
                raise action
            if action == "hang":
                await asyncio.sleep(5)
            return ProviderResponse(
                answer=_valid_output("elyra-stage09-request-001"),
                provider=provider_id,
                model=model,
            )

        return generate

    for provider_id, adapter in ADAPTERS.items():
        monkeypatch.setattr(adapter, "generate_response", make(provider_id))
    return calls


def post_elyra(**overrides):
    payload = _payload(provider="auto", allow_real_provider=True, allow_mock_fallback=False)
    payload.update(overrides)
    return client.post("/api/orchestrate", json=payload, headers={AUTH_HEADER: ELYRA_KEY})


def reasons(data) -> dict[str, str | None]:
    return {
        item["provider_id"]: item["elimination_reason"]
        for item in data["audit"]["routing_candidates_considered"]
    }


def model_of(provider_id: str) -> str:
    return provider_catalog_service.default_model_for(provider_id).model_id


# ---------------------------------------------------------------------------
# Fonte única de candidatos
# ---------------------------------------------------------------------------
def test_candidate_sources_are_the_catalog_not_a_fixed_tuple(monkeypatch):
    assert auto_real_provider_candidates() == ("gemini",)
    assert provider_catalog_service.routing_candidate_ids() == (
        "gemini",
        "claude",
        "openai",
        "deepseek",
        "grok",
    )

    homologate(monkeypatch, "grok")

    # Homologar no catálogo é suficiente para o provider virar candidato:
    # nenhum outro arquivo precisa mudar.
    assert auto_real_provider_candidates() == ("gemini", "grok")


# ---------------------------------------------------------------------------
# A. Consumer comum envia auto e nenhum modelo
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "overrides",
    [
        {"provider": "claude"},
        {"provider": "gemini"},
        {"model": "gemini-3.5-flash"},
        {"model": "claude-sonnet-4-5"},
    ],
)
def test_A_common_consumer_cannot_pick_provider_or_model(monkeypatch, overrides):
    configure(monkeypatch, "gemini", "claude")
    homologate(monkeypatch, "claude")
    calls = fake_adapters(monkeypatch)

    data = post_elyra(**overrides).json()

    assert data["status"] == "blocked"
    assert calls == []


# ---------------------------------------------------------------------------
# B. Somente Gemini homologado
# ---------------------------------------------------------------------------
def test_B_only_gemini_homologated_selects_gemini(monkeypatch):
    configure(monkeypatch, *ADAPTERS)  # todas as chaves presentes
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["status"] == "ok"
    assert data["provider_used"] == "gemini"
    assert calls == [("gemini", model_of("gemini"))]
    explained = reasons(data)
    assert explained["gemini"] is None
    for provider_id in ("claude", "openai", "deepseek", "grok"):
        # D: configurado não é homologado.
        assert explained[provider_id] == EliminationReason.NOT_HOMOLOGATED.value
    assert data["audit"]["routing_policy_version"] == POLICY_VERSION


# ---------------------------------------------------------------------------
# C. Gemini + Claude homologados: a política escolhe
# ---------------------------------------------------------------------------
def test_C1_both_homologated_catalog_priority_selects_gemini(monkeypatch):
    configure(monkeypatch, "gemini", "claude")
    homologate(monkeypatch, "claude")
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["provider_used"] == "gemini"
    assert calls == [("gemini", model_of("gemini"))]
    assert reasons(data)["claude"] is None  # elegível, apenas não primeiro


def test_C2_project_task_preference_selects_claude_and_elyra_contract_holds(
    monkeypatch,
):
    configure(monkeypatch, "gemini", "claude")
    homologate(monkeypatch, "claude")
    monkeypatch.setattr(
        routing_module,
        "_PRIORITY_BY_PROJECT_TASK",
        {("elyra", ELYRA_TASK): ("claude", "gemini")},
    )
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["status"] == "ok"
    assert data["provider_requested"] == "auto"
    assert data["provider_used"] == "claude"
    assert data["model"] == model_of("claude")
    assert data["fallback_used"] is False
    assert data["elyra"]["correlationId"] == "elyra-stage09-request-001"
    assert calls == [("claude", model_of("claude"))]
    assert data["audit"]["real_provider_attempt_count"] == 1


def test_C3_missing_capability_eliminates_provider_deterministically(monkeypatch):
    configure(monkeypatch, "gemini", "claude")
    homologate(monkeypatch, "claude")
    specs = {k: dict(v) for k, v in catalog_module._STATIC_SPECS.items()}
    specs["gemini"]["capabilities"] = ()  # sem TEXT_GENERATION declarado
    monkeypatch.setattr(catalog_module, "_STATIC_SPECS", specs)
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["provider_used"] == "claude"
    assert reasons(data)["gemini"] == EliminationReason.CAPABILITY_MISSING.value
    assert calls == [("claude", model_of("claude"))]


def test_C4_task_level_capability_requirement_is_a_filter(monkeypatch):
    configure(monkeypatch, "gemini", "claude")
    homologate(monkeypatch, "claude")
    monkeypatch.setattr(
        routing_module,
        "_REQUIRED_CAPABILITIES_BY_TASK",
        {ELYRA_TASK: (ProviderCapability.RELEASE_GATE_DECISION,)},
    )
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["status"] == "blocked"
    assert calls == []
    assert set(reasons(data).values()) >= {EliminationReason.CAPABILITY_MISSING.value}


def test_C5_legacy_mode_never_promotes_a_second_provider(monkeypatch):
    monkeypatch.setenv(FLAG_ROUTING_MODE, RoutingMode.LEGACY.value)
    configure(monkeypatch, "gemini", "claude")
    homologate(monkeypatch, "claude")
    monkeypatch.setattr(
        routing_module,
        "_PRIORITY_BY_PROJECT_TASK",
        {("elyra", ELYRA_TASK): ("claude", "gemini")},
    )
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    # Legacy ignora a preferência do motor: primeiro candidato configurado
    # do catálogo, uma tentativa, nenhum segundo provider.
    assert data["provider_used"] == "gemini"
    assert calls == [("gemini", model_of("gemini"))]


# ---------------------------------------------------------------------------
# D/E. Configurado sem homologação; homologado sem autorização
# ---------------------------------------------------------------------------
def test_D_configured_but_not_homologated_never_enters_auto(monkeypatch):
    configure(monkeypatch, "claude")  # Gemini sem chave
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["status"] == "blocked"
    assert calls == []
    assert reasons(data)["claude"] == EliminationReason.NOT_HOMOLOGATED.value
    assert "claude" not in auto_real_provider_candidates()


def test_E_homologated_but_not_authorized_for_elyra_never_enters_auto(monkeypatch):
    configure(monkeypatch, "claude")
    homologate(monkeypatch, "claude", authorize_projects=frozenset({"finguard"}))
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["status"] == "blocked"
    assert calls == []
    assert reasons(data)["claude"] == EliminationReason.NOT_AUTHORIZED.value


# ---------------------------------------------------------------------------
# F. Modelo não homologado
# ---------------------------------------------------------------------------
def test_F_provider_homologated_with_non_homologated_model_is_blocked(monkeypatch):
    configure(monkeypatch, "claude")
    homologate(monkeypatch, "claude", model_homologated=False)
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["status"] == "blocked"
    assert calls == []
    assert reasons(data)["claude"] == EliminationReason.MODEL_NOT_HOMOLOGATED.value


# ---------------------------------------------------------------------------
# G. Circuit open elimina antes do adapter
# ---------------------------------------------------------------------------
def test_G_open_circuit_eliminates_before_adapter(monkeypatch):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    configure(monkeypatch, "gemini", "claude")
    homologate(monkeypatch, "claude")
    provider_health_service.record(
        provider_health_service.key("development", "gemini", model_of("gemini")),
        FailureClassification.COMPLETION_AMBIGUOUS,
    )
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["provider_used"] == "claude"
    assert reasons(data)["gemini"] == EliminationReason.CIRCUIT_OPEN.value
    assert calls == [("claude", model_of("claude"))]


def test_G_circuit_is_per_model_not_global_per_provider(monkeypatch):
    monkeypatch.setenv(FLAG_CIRCUIT_ENABLED, "true")
    configure(monkeypatch, "gemini")
    provider_health_service.record(
        provider_health_service.key("development", "gemini", "outro-modelo"),
        FailureClassification.COMPLETION_AMBIGUOUS,
    )
    provider_health_service.record(
        provider_health_service.key("staging", "gemini", model_of("gemini")),
        FailureClassification.COMPLETION_AMBIGUOUS,
    )
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["provider_used"] == "gemini"
    assert calls == [("gemini", model_of("gemini"))]


# ---------------------------------------------------------------------------
# H. Provider indisponível
# ---------------------------------------------------------------------------
def test_H_unconfigured_primary_is_routed_around_before_any_dispatch(monkeypatch):
    configure(monkeypatch, "claude")  # Gemini sem chave
    homologate(monkeypatch, "claude")
    calls = fake_adapters(monkeypatch)

    data = post_elyra().json()

    assert data["provider_used"] == "claude"
    assert reasons(data)["gemini"] == EliminationReason.NOT_CONFIGURED.value
    assert calls == [("claude", model_of("claude"))]
    assert data["fallback_used"] is False


def test_H_elyra_failure_after_dispatch_never_starts_secondary(monkeypatch):
    monkeypatch.setenv(FLAG_REAL_FALLBACK_ENABLED, "true")
    configure(monkeypatch, "gemini", "claude")
    homologate(monkeypatch, "claude")
    from app.modules.providers.base import ProviderExecutionError

    calls = fake_adapters(monkeypatch, {"gemini": ProviderExecutionError("falha sintética")})

    data = post_elyra().json()

    # Task Elyra fora da allowlist de fallback real; Elyra também recusa
    # fallback. Uma tentativa, nenhum secundário.
    assert data["status"] == "blocked"
    assert calls == [("gemini", model_of("gemini"))]
    assert data["audit"]["real_fallback_attempted"] is False


# ---------------------------------------------------------------------------
# I. Timeout ambíguo
# ---------------------------------------------------------------------------
def test_I_ambiguous_timeout_never_dispatches_second_provider(monkeypatch):
    monkeypatch.setenv(FLAG_REAL_FALLBACK_ENABLED, "true")
    monkeypatch.setenv("PEDROCORE_PROVIDER_TIMEOUT_SECONDS", "0.05")
    configure(monkeypatch, "gemini", "claude")
    homologate(monkeypatch, "claude")
    calls = fake_adapters(monkeypatch, {"gemini": "hang"})

    # assistant_chat está na allowlist de fallback: é o caso mais permissivo.
    data = client.post(
        "/api/orchestrate",
        json={
            "message": "Pergunta sintética multiprovider.",
            "provider": "auto",
            "task_type": "assistant_chat",
            "origin_system": "finguard",
            "allow_real_provider": True,
        },
        headers={AUTH_HEADER: FINGUARD_KEY},
    ).json()

    assert [provider for provider, _ in calls] == ["gemini"]
    assert data["error_code"] == codes.PROVIDER_TIMEOUT
    assert data["audit"]["real_fallback_attempted"] is False
    assert data["provider_used"] in {"mock", "none"}
