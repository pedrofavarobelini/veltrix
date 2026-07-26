"""Identidade autenticada e autorização por projeto (Etapa 2).

Prova que a identidade do caller vem da CREDENCIAL (não do payload), que
`origin_system` é apenas uma alegação validada, que provider real depende de
autorização explícita por projeto/papel/ambiente (fail-closed) e que
`allow_real_provider=true` sozinho nunca libera provider real.

Nenhum teste usa rede, chave real ou smoke real: providers reais são
substituídos por stubs determinísticos.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.schemas import (
    SHARED_OR_UNKNOWN_PROJECT_ID,
    CallerRole,
    IdentityStrength,
    OriginValidation,
)
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
    caller_identity_service,
    credential_fingerprint,
)
from app.modules.contracts import codes
from app.modules.orchestration.service import AUTO_REAL_PROVIDER_CANDIDATES
from app.modules.provider_authorization.service import provider_authorization_service
from app.modules.provider_catalog.service import provider_catalog_service
from app.modules.providers.base import ProviderExecutionError, ProviderResponse
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.openai_provider import OpenAIProvider

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FAKE_PROVIDER_KEY = "test-provider-key-never-leak"

FINGUARD_CREDENTIAL = "finguard-credencial-de-teste-nunca-real"
TOOL_CREDENTIAL = "ferramenta-credencial-de-teste-nunca-real"
GHOST_CREDENTIAL = "projeto-desconhecido-credencial-de-teste"

REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-app",
            "api_key": FINGUARD_CREDENTIAL,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
        },
        {
            "credential_id": "pedrocore-tool",
            "api_key": TOOL_CREDENTIAL,
            "project_id": "pedrocore",
            "role": "technical_tool",
            "environment": "development",
        },
        {
            "credential_id": "ghost-tool",
            "api_key": GHOST_CREDENTIAL,
            "project_id": "projeto-sem-autorizacao",
            "role": "technical_tool",
            "environment": "development",
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
    return REGISTRY


@pytest.fixture
def provider_stub(monkeypatch):
    """Substitui todo provider real por stub: registra chamadas, sem rede."""
    calls: list[str] = []

    def install(failing: set[str] | None = None):
        failing = failing or set()

        def make(name: str):
            async def stub(self, message, mode, model=None, system_prompt=None):
                calls.append(name)
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


def _configure_keys(monkeypatch, **overrides):
    defaults = {
        "gemini_api_key": "",
        "anthropic_api_key": "",
        "openai_api_key": "",
        "deepseek_api_key": "",
        "xai_api_key": "",
    }
    defaults.update(overrides)
    for attribute, value in defaults.items():
        monkeypatch.setattr(settings, attribute, value)


def _post(credential: str | None, **payload_overrides):
    payload = {
        "message": "Pergunta segura de identidade.",
        "provider": "auto",
        "task_type": "assistant_chat",
        "origin_system": "finguard",
        "allow_real_provider": True,
    }
    payload.update(payload_overrides)
    headers = {AUTH_HEADER: credential} if credential else {}
    return client.post("/api/orchestrate", json=payload, headers=headers)


# ---------------------------------------------------------------------------
# Identidade derivada da credencial
# ---------------------------------------------------------------------------
def test_valid_credential_derives_project_id(registry):
    resolution = caller_identity_service.resolve(FINGUARD_CREDENTIAL)

    assert resolution.rejected is False
    assert resolution.context.project_id == "finguard"
    assert resolution.context.identity_is_project_bound is True


def test_valid_credential_derives_caller_role(registry):
    consumer = caller_identity_service.resolve(FINGUARD_CREDENTIAL).context
    tool = caller_identity_service.resolve(TOOL_CREDENTIAL).context

    assert consumer.caller_role is CallerRole.COMMON_CONSUMER
    assert tool.caller_role is CallerRole.TECHNICAL_TOOL


def test_valid_credential_derives_environment(registry):
    context = caller_identity_service.resolve(FINGUARD_CREDENTIAL).context

    assert context.environment == "development"
    assert context.authenticated is True


def test_unknown_credential_is_rejected(registry):
    resolution = caller_identity_service.resolve("credencial-que-nao-existe")

    assert resolution.rejected is True
    assert resolution.error_code == codes.CALLER_CREDENTIAL_UNKNOWN

    response = _post("credencial-que-nao-existe", provider="mock")
    assert response.status_code == 401
    assert response.json()["error_code"] == codes.CALLER_CREDENTIAL_UNKNOWN


def test_missing_credential_with_registry_is_rejected(registry):
    response = _post(None, provider="mock")

    assert response.status_code == 401
    assert response.json()["error_code"] == codes.CALLER_CREDENTIAL_MISSING


def test_invalid_registry_is_fail_closed(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, "{isto nao e json valido")

    response = _post(FINGUARD_CREDENTIAL, provider="mock")

    assert response.status_code == 401
    assert response.json()["error_code"] == codes.CALLER_REGISTRY_INVALID


# ---------------------------------------------------------------------------
# origin_system como alegação validada
# ---------------------------------------------------------------------------
def test_compatible_origin_is_accepted(registry, provider_stub, monkeypatch):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    provider_stub()

    data = _post(FINGUARD_CREDENTIAL, origin_system="finguard").json()

    assert data["status"] == "ok"
    assert data["project_id"] == "finguard"
    assert data["audit"]["origin_validation"] == OriginValidation.MATCH.value


def test_incompatible_origin_is_rejected_not_silently_corrected(registry, provider_stub):
    calls = provider_stub()

    data = _post(FINGUARD_CREDENTIAL, origin_system="pedrocore").json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.CALLER_ORIGIN_MISMATCH
    assert data["provider_used"] == "none"
    # A origem declarada continua ecoada como alegação; não foi "corrigida".
    assert data["origin_system"] == "pedrocore"
    assert data["audit"]["project_id_authenticated"] == "finguard"
    assert calls == []


def test_payload_cannot_change_project_of_a_bound_credential(registry, provider_stub):
    provider_stub()

    data = _post(FINGUARD_CREDENTIAL, origin_system="finguard").json()

    assert data["project_id"] == "finguard"
    assert data["audit"]["project_id_authenticated"] == "finguard"


# ---------------------------------------------------------------------------
# Restrições do consumidor comum
# ---------------------------------------------------------------------------
def test_common_consumer_cannot_select_provider(registry, provider_stub, monkeypatch):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(FINGUARD_CREDENTIAL, provider="gemini").json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.CALLER_PROVIDER_SELECTION_NOT_ALLOWED
    assert data["provider_used"] == "none"
    assert calls == []


def test_common_consumer_cannot_send_arbitrary_model(registry, provider_stub, monkeypatch):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(FINGUARD_CREDENTIAL, provider="auto", model="gemini-2.5-pro").json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.CALLER_MODEL_SELECTION_NOT_ALLOWED
    assert calls == []


def test_common_consumer_keeps_auto_and_safe_local_selections(registry, provider_stub):
    provider_stub()

    for provider in ("auto", "mock", "local_qa"):
        data = _post(
            FINGUARD_CREDENTIAL, provider=provider, allow_real_provider=False
        ).json()
        assert data["status"] == "ok", provider
        assert data["error_code"] != codes.CALLER_PROVIDER_SELECTION_NOT_ALLOWED


# ---------------------------------------------------------------------------
# Matriz de autorização
# ---------------------------------------------------------------------------
def test_authorized_technical_tool_keeps_explicit_selection(
    registry, provider_stub, monkeypatch
):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(
        TOOL_CREDENTIAL, provider="gemini", origin_system="pedrocore"
    ).json()

    assert data["provider_used"] == "gemini"
    assert data["fallback_used"] is False
    assert calls == ["gemini"]
    assert data["audit"]["authorization_result"] == "allowed"


def test_unauthorized_technical_tool_is_rejected(registry, provider_stub, monkeypatch):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(
        GHOST_CREDENTIAL, provider="gemini", origin_system="projeto-sem-autorizacao"
    ).json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert data["error_code"] == codes.PROVIDER_NOT_AUTHORIZED_FOR_PROJECT
    assert calls == []


def test_configured_but_non_homologated_provider_model_is_blocked(
    registry, provider_stub, monkeypatch
):
    _configure_keys(monkeypatch, anthropic_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(TOOL_CREDENTIAL, provider="claude", origin_system="pedrocore").json()

    assert data["status"] == "blocked"
    assert data["provider_used"] == "none"
    assert data["error_code"] == codes.MODEL_NOT_AUTHORIZED
    assert calls == []


def test_implemented_but_not_homologated_provider_is_never_eligible(monkeypatch):
    _configure_keys(
        monkeypatch, anthropic_api_key=FAKE_PROVIDER_KEY, openai_api_key=FAKE_PROVIDER_KEY
    )

    for provider_id in ("claude", "openai"):
        definition = provider_catalog_service.get(provider_id)
        assert definition.implemented is True
        assert definition.configured is True
        assert definition.is_approved_for_production is False

        decision = provider_authorization_service.evaluate(
            identity_strength=IdentityStrength.REGISTERED,
            project_id="finguard",
            caller_role=CallerRole.COMMON_CONSUMER,
            environment="development",
            provider_id=provider_id,
        )
        assert decision.denied is True
        assert decision.error_code == codes.PROVIDER_NOT_HOMOLOGATED


def test_unknown_project_never_reaches_a_real_provider(registry, provider_stub, monkeypatch):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(
        GHOST_CREDENTIAL, provider="auto", origin_system="projeto-sem-autorizacao"
    ).json()

    assert data["provider_used"] == "mock"
    assert data["error_code"] == codes.PROVIDER_NOT_AUTHORIZED_FOR_PROJECT
    assert calls == []


def test_allow_real_provider_true_without_project_authorization_is_rejected(
    registry, provider_stub, monkeypatch
):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(
        GHOST_CREDENTIAL,
        provider="auto",
        origin_system="projeto-sem-autorizacao",
        allow_real_provider=True,
    ).json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert calls == []


def test_allow_real_provider_false_preserves_safe_mode_block(
    registry, provider_stub, monkeypatch
):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(FINGUARD_CREDENTIAL, allow_real_provider=False).json()

    assert data["safe_mode_blocked"] is True
    assert data["provider_used"] == "mock"
    assert codes.PROVIDER_REAL_BLOCKED in data["warning_codes"]
    assert calls == []


def test_authorization_matrix_defaults_to_deny():
    for project in ("projeto-inexistente", "unknown", SHARED_OR_UNKNOWN_PROJECT_ID, ""):
        decision = provider_authorization_service.evaluate(
            identity_strength=IdentityStrength.REGISTERED,
            project_id=project,
            caller_role=CallerRole.TECHNICAL_TOOL,
            environment="development",
            provider_id="gemini",
        )
        assert decision.denied is True, project

    for provider_id in ("claude", "openai", "deepseek", "grok"):
        decision = provider_authorization_service.evaluate(
            identity_strength=IdentityStrength.REGISTERED,
            project_id="finguard",
            caller_role=CallerRole.COMMON_CONSUMER,
            environment="development",
            provider_id=provider_id,
        )
        assert decision.denied is True, provider_id

    # Identidade ambígua é negada mesmo com projeto e ambiente registrados.
    ambiguous = provider_authorization_service.evaluate(
        identity_strength=IdentityStrength.AMBIGUOUS,
        project_id="finguard",
        caller_role=CallerRole.COMMON_CONSUMER,
        environment="development",
        provider_id="gemini",
    )
    assert ambiguous.denied is True
    assert ambiguous.error_code == codes.CALLER_IDENTITY_AMBIGUOUS

    # Produção não é herdada por wildcard: exige credencial registrada.
    local_production = provider_authorization_service.evaluate(
        identity_strength=IdentityStrength.LOCAL_TRUSTED,
        project_id="finguard",
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="production",
        provider_id="gemini",
    )
    assert local_production.denied is True


# ---------------------------------------------------------------------------
# Políticas preexistentes preservadas
# ---------------------------------------------------------------------------
def test_safe_mode_still_prevails_over_authorization(registry, provider_stub, monkeypatch):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(TOOL_CREDENTIAL, origin_system="pedrocore", allow_real_provider=False).json()

    assert data["safe_mode_blocked"] is True
    assert data["error_code"] == codes.PROVIDER_REAL_BLOCKED
    assert calls == []


def test_critical_task_policy_is_preserved(registry, provider_stub):
    provider_stub()

    data = _post(
        FINGUARD_CREDENTIAL,
        provider="local_qa",
        task_type="release_gate_review",
        allow_real_provider=False,
        artifacts=[{"type": "qa_report", "content": "3 tests failed with AssertionError"}],
    ).json()

    assert data["release_gate"]["can_advance"] is False
    assert codes.RELEASE_GATE_BLOCKED in data["warning_codes"]


def test_mock_stays_available_for_unknown_origin_without_real_call(
    registry, provider_stub, monkeypatch
):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = _post(
        GHOST_CREDENTIAL,
        provider="mock",
        origin_system="projeto-sem-autorizacao",
        allow_real_provider=False,
    ).json()

    assert data["status"] == "ok"
    assert data["provider_used"] == "mock"
    assert data["answer"]
    assert calls == []


def test_local_qa_remains_compatible(registry, provider_stub):
    calls = provider_stub()

    data = _post(
        FINGUARD_CREDENTIAL,
        provider="local_qa",
        task_type="qa_report_analysis",
        allow_real_provider=False,
        artifacts=[{"type": "qa_report", "content": "125 passed, 0 failed."}],
    ).json()

    assert data["provider_used"] == "local_qa"
    assert data["model"] == "local-qa-v1"
    assert calls == []


def test_legacy_explicit_technical_selection_is_not_broken(
    monkeypatch, provider_stub
):
    """Sem autenticação configurada (modo dev/local), o operador local mantém
    a seleção explícita — mas apenas para o próprio projeto `pedrocore`."""
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    calls = provider_stub()

    data = client.post(
        "/api/orchestrate",
        json={
            "message": "Teste técnico local",
            "provider": "gemini",
            "origin_system": "pedrocore",
            "task_type": "assistant_chat",
            "allow_real_provider": True,
        },
    ).json()

    assert data["provider_used"] == "gemini"
    assert calls == ["gemini"]
    assert data["audit"]["identity_strength"] == IdentityStrength.LOCAL_TRUSTED.value


# ---------------------------------------------------------------------------
# Regressão da Etapa 1 sob a nova camada de identidade
# ---------------------------------------------------------------------------
def test_auto_remains_gemini_only_under_authorization(
    registry, provider_stub, monkeypatch
):
    _configure_keys(
        monkeypatch,
        gemini_api_key=FAKE_PROVIDER_KEY,
        anthropic_api_key=FAKE_PROVIDER_KEY,
        openai_api_key=FAKE_PROVIDER_KEY,
    )
    calls = provider_stub()

    data = _post(FINGUARD_CREDENTIAL).json()

    assert AUTO_REAL_PROVIDER_CANDIDATES == ("gemini",)
    assert data["provider_used"] == "gemini"
    assert calls == ["gemini"]


def test_gemini_failure_still_goes_to_mock_never_to_claude(
    registry, provider_stub, monkeypatch
):
    _configure_keys(
        monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY, anthropic_api_key=FAKE_PROVIDER_KEY
    )
    calls = provider_stub(failing={"gemini"})

    data = _post(FINGUARD_CREDENTIAL).json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert calls == ["gemini"]


def test_no_request_calls_two_real_providers(registry, provider_stub, monkeypatch):
    _configure_keys(
        monkeypatch,
        gemini_api_key=FAKE_PROVIDER_KEY,
        anthropic_api_key=FAKE_PROVIDER_KEY,
        openai_api_key=FAKE_PROVIDER_KEY,
        deepseek_api_key=FAKE_PROVIDER_KEY,
        xai_api_key=FAKE_PROVIDER_KEY,
    )
    calls = provider_stub(failing={"gemini"})

    for credential, provider, origin in (
        (FINGUARD_CREDENTIAL, "auto", "finguard"),
        (TOOL_CREDENTIAL, "gemini", "pedrocore"),
        (TOOL_CREDENTIAL, "claude", "pedrocore"),
        (GHOST_CREDENTIAL, "auto", "projeto-sem-autorizacao"),
    ):
        calls.clear()
        _post(credential, provider=provider, origin_system=origin)
        assert len(calls) <= 1, (credential, provider, calls)


# ---------------------------------------------------------------------------
# Segredos
# ---------------------------------------------------------------------------
def test_credential_never_appears_in_audit_or_response(registry, provider_stub, monkeypatch):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    provider_stub()

    data = _post(FINGUARD_CREDENTIAL).json()
    dumped = json.dumps(data, ensure_ascii=False)

    assert FINGUARD_CREDENTIAL not in dumped
    assert FAKE_PROVIDER_KEY not in dumped
    assert data["audit"]["credential_id"] == "finguard-app"
    assert data["audit"]["authenticated"] is True


def test_credential_never_appears_in_logs(registry, provider_stub, monkeypatch, caplog):
    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    provider_stub()

    with caplog.at_level("DEBUG"):
        _post(FINGUARD_CREDENTIAL)

    assert FINGUARD_CREDENTIAL not in caplog.text
    assert FAKE_PROVIDER_KEY not in caplog.text


def test_fingerprint_cannot_reconstruct_the_credential():
    fingerprint = credential_fingerprint(FINGUARD_CREDENTIAL)
    other = credential_fingerprint(TOOL_CREDENTIAL)

    assert FINGUARD_CREDENTIAL not in fingerprint
    assert fingerprint != other
    assert fingerprint == credential_fingerprint(FINGUARD_CREDENTIAL)
    # Truncado de propósito: não é hash completo reutilizável como credencial.
    assert len(fingerprint) == len("fp_") + 12


def test_shared_credential_is_authenticated_but_never_identified(
    monkeypatch, provider_stub
):
    """Uma única API key global autentica, mas não identifica projeto."""
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, "chave-global-de-teste")
    provider_stub()

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Teste",
            "provider": "mock",
            "origin_system": "finguard",
            "task_type": "assistant_chat",
        },
        headers={AUTH_HEADER: "chave-global-de-teste"},
    )
    data = response.json()
    audit = data["audit"]

    assert response.status_code == 200
    assert audit["authenticated"] is True
    assert audit["identity_strength"] == IdentityStrength.AMBIGUOUS.value
    assert audit["origin_validation"] == OriginValidation.NOT_TRUSTED.value
    assert audit["project_id_authenticated"] == SHARED_OR_UNKNOWN_PROJECT_ID
    assert audit["caller_role"] == CallerRole.COMMON_CONSUMER.value
    assert audit["credential_id"].startswith("internal-shared-fp_")
    assert "chave-global-de-teste" not in json.dumps(data, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Contrato público do FinGuard
# ---------------------------------------------------------------------------
def test_public_response_has_no_caller_metadata_for_the_frontend(
    registry, provider_stub, monkeypatch
):
    from app.modules.orchestration.schemas import AssistantResponsePayload

    _configure_keys(monkeypatch, gemini_api_key=FAKE_PROVIDER_KEY)
    provider_stub()

    _post(FINGUARD_CREDENTIAL)
    frontend_fields = set(AssistantResponsePayload.model_fields)

    assert {"answer", "suggestions", "disclaimer"} <= frontend_fields
    for forbidden in (
        "credential_id",
        "caller_role",
        "environment",
        "project_id_authenticated",
        "authorization_result",
    ):
        assert forbidden not in frontend_fields
