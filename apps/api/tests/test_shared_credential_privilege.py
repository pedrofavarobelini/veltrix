"""Menor privilégio para credencial compartilhada (fix de segurança).

Regressão da vulnerabilidade encontrada na revisão da Etapa 2: a API key
global compartilhada recebia `caller_role=technical_tool` e derivava o
`project_id` do `origin_system` declarado, o que permitia:

    chave global → declara origin_system=finguard → assume projeto FinGuard
    → passa na matriz → alcança o adapter real do Gemini

Agora `autenticado != identificado de forma inequívoca != autorizado para
provider real`. Todos os testes usam credenciais sintéticas e spy de provider:
nenhuma chamada externa é possível.
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
)
from app.modules.contracts import codes
from app.modules.orchestration.schemas import AssistantResponsePayload
from app.modules.orchestration.service import AUTO_REAL_PROVIDER_CANDIDATES
from app.modules.providers.base import ProviderExecutionError, ProviderResponse
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.openai_provider import OpenAIProvider

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"

GLOBAL_SHARED_KEY = "chave-global-compartilhada-sintetica"
FINGUARD_REGISTERED_KEY = "finguard-registrada-sintetica"
FINGUARD_TOOL_KEY = "finguard-tecnica-registrada-sintetica"
FAKE_PROVIDER_KEY = "chave-provider-sintetica-nunca-real"

REAL_PROVIDER_CLASSES = (
    GeminiProvider,
    OpenAIProvider,
    ClaudeProvider,
    DeepSeekProvider,
    GrokProvider,
)

REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-app",
            "api_key": FINGUARD_REGISTERED_KEY,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
        },
        {
            "credential_id": "finguard-tool",
            "api_key": FINGUARD_TOOL_KEY,
            "project_id": "finguard",
            "role": "technical_tool",
            "environment": "development",
            "allowed_origins": ["finguard"],
        },
    ]
)


@pytest.fixture
def all_providers_configured(monkeypatch):
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
    """Spy em TODOS os adapters reais: nenhuma chamada externa é possível."""
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


@pytest.fixture
def global_shared_key(monkeypatch):
    """Único modo operacional atual: uma API key global compartilhada."""
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, GLOBAL_SHARED_KEY)


@pytest.fixture
def registered_credentials(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, REGISTRY)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)


def _post(credential: str | None, **overrides):
    payload = {
        "message": "Pergunta segura de regressão de identidade.",
        "provider": "auto",
        "task_type": "assistant_chat",
        "origin_system": "finguard",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    headers = {AUTH_HEADER: credential} if credential else {}
    return client.post("/api/orchestrate", json=payload, headers=headers)


# ---------------------------------------------------------------------------
# 1-2. A chave global não vira ferramenta técnica nem deriva projeto
# ---------------------------------------------------------------------------
def test_global_shared_key_is_not_technical_tool(global_shared_key):
    context = caller_identity_service.resolve(GLOBAL_SHARED_KEY).context

    assert context.authenticated is True
    assert context.caller_role is CallerRole.COMMON_CONSUMER
    assert context.identity_strength is IdentityStrength.AMBIGUOUS
    assert context.identity_is_project_bound is False
    assert context.establishes_project_identity is False


def test_global_shared_key_does_not_derive_project_from_origin(global_shared_key):
    context = caller_identity_service.resolve(GLOBAL_SHARED_KEY).context

    claim = caller_identity_service.validate_origin_claim(context, "finguard", "finguard")

    assert claim.identity_project_id == SHARED_OR_UNKNOWN_PROJECT_ID
    assert claim.validation is OriginValidation.NOT_TRUSTED
    # O Project Context (policy/tasks) continua derivado da alegação, sem
    # qualquer privilégio de identidade.
    assert claim.context_project_id == "finguard"


# ---------------------------------------------------------------------------
# 3-7. A chave global não alcança provider real por nenhum caminho
# ---------------------------------------------------------------------------
def test_global_shared_key_claiming_finguard_never_reaches_gemini(
    global_shared_key, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(GLOBAL_SHARED_KEY, provider="auto").json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert data["error_code"] == codes.CALLER_IDENTITY_AMBIGUOUS
    assert data["audit"]["project_id_authenticated"] == SHARED_OR_UNKNOWN_PROJECT_ID
    assert calls == []


def test_global_shared_key_with_allow_real_provider_never_reaches_gemini(
    global_shared_key, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    for origin in ("finguard", "finguard-local", "pedrocore", "origem-inventada"):
        calls.clear()
        data = _post(GLOBAL_SHARED_KEY, provider="auto", origin_system=origin).json()

        assert data["provider_used"] == "mock", origin
        assert data["audit"]["authorization_result"] == "denied", origin
        assert calls == [], origin


def test_global_shared_key_with_explicit_provider_is_blocked(
    global_shared_key, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    for provider in ("gemini", "claude", "openai"):
        data = _post(GLOBAL_SHARED_KEY, provider=provider).json()

        assert data["status"] == "blocked", provider
        assert data["error_code"] == codes.CALLER_PROVIDER_SELECTION_NOT_ALLOWED, provider
        assert data["provider_used"] == "none", provider
    assert calls == []


def test_global_shared_key_with_model_is_blocked(
    global_shared_key, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(GLOBAL_SHARED_KEY, provider="auto", model="gemini-2.5-pro").json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.CALLER_MODEL_SELECTION_NOT_ALLOWED
    assert calls == []


def test_no_real_adapter_is_ever_touched_by_the_shared_key(
    global_shared_key, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    scenarios = [
        {"provider": "auto", "allow_real_provider": True},
        {"provider": "auto", "allow_real_provider": False},
        {"provider": "gemini", "allow_real_provider": True},
        {"provider": "claude", "allow_real_provider": True},
        {"provider": "mock", "allow_real_provider": True},
        {"provider": "local_qa", "allow_real_provider": True},
        {"provider": "auto", "allow_real_provider": True, "model": "qualquer-modelo"},
    ]
    for scenario in scenarios:
        _post(GLOBAL_SHARED_KEY, **scenario)

    assert calls == []


def test_shared_key_denial_is_identity_violation_not_provider_failure(
    global_shared_key, all_providers_configured, adapter_spy
):
    """Negação por identidade não pode ser confundida com falha operacional."""
    adapter_spy()

    data = _post(GLOBAL_SHARED_KEY, provider="auto").json()

    assert data["error_code"] == codes.CALLER_IDENTITY_AMBIGUOUS
    assert data["error_code"] != codes.PROVIDER_REAL_UNAVAILABLE
    assert codes.CALLER_IDENTITY_AMBIGUOUS in data["warning_codes"]
    assert data["audit"]["authorization_reason_code"] == codes.CALLER_IDENTITY_AMBIGUOUS


# ---------------------------------------------------------------------------
# 8-10. Credencial registrada estabelece identidade confiável
# ---------------------------------------------------------------------------
def test_registered_finguard_credential_derives_the_right_project(
    registered_credentials, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(FINGUARD_REGISTERED_KEY, provider="auto").json()
    audit = data["audit"]

    assert audit["identity_strength"] == IdentityStrength.REGISTERED.value
    assert audit["project_id_authenticated"] == "finguard"
    assert audit["origin_validation"] == OriginValidation.MATCH.value
    assert data["provider_used"] == "gemini"
    assert calls == ["gemini"]


def test_registered_credential_rejects_incompatible_origin(
    registered_credentials, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(FINGUARD_REGISTERED_KEY, origin_system="pedrocore").json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.CALLER_ORIGIN_MISMATCH
    assert data["provider_used"] == "none"
    assert calls == []


def test_registered_technical_credential_keeps_explicit_selection_inside_matrix(
    registered_credentials, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    allowed = _post(FINGUARD_TOOL_KEY, provider="gemini").json()
    assert allowed["provider_used"] == "gemini"
    assert calls == ["gemini"]

    calls.clear()
    # Modelo/provider não homologado é bloqueado antes de qualquer adapter.
    denied = _post(FINGUARD_TOOL_KEY, provider="claude").json()
    assert denied["status"] == "blocked"
    assert denied["provider_used"] == "none"
    assert denied["error_code"] == codes.MODEL_NOT_AUTHORIZED
    assert calls == []


# ---------------------------------------------------------------------------
# 11-15. Fail-closed, auto Gemini-only e compatibilidade
# ---------------------------------------------------------------------------
def test_unknown_caller_stays_fail_closed(
    registered_credentials, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    unknown = _post("credencial-que-nao-existe").json()
    missing = _post(None).json()

    assert unknown["error_code"] == codes.CALLER_CREDENTIAL_UNKNOWN
    assert missing["error_code"] == codes.CALLER_CREDENTIAL_MISSING
    assert calls == []


def test_auto_remains_gemini_only_for_authorized_callers(
    registered_credentials, all_providers_configured, adapter_spy
):
    calls = adapter_spy()

    data = _post(FINGUARD_REGISTERED_KEY, provider="auto").json()

    assert AUTO_REAL_PROVIDER_CANDIDATES == ("gemini",)
    assert data["provider_used"] == "gemini"
    assert calls == ["gemini"]
    assert "claude" not in calls and "openai" not in calls


def test_authorized_gemini_failure_falls_back_to_mock_never_to_claude(
    registered_credentials, all_providers_configured, adapter_spy
):
    calls = adapter_spy(failing={"gemini"})

    data = _post(FINGUARD_REGISTERED_KEY, provider="auto").json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert calls == ["gemini"]


def test_no_request_executes_two_real_providers(
    registered_credentials, all_providers_configured, adapter_spy
):
    calls = adapter_spy(failing={"gemini"})

    for credential, provider in (
        (FINGUARD_REGISTERED_KEY, "auto"),
        (FINGUARD_TOOL_KEY, "gemini"),
        (FINGUARD_TOOL_KEY, "claude"),
        (FINGUARD_REGISTERED_KEY, "mock"),
    ):
        calls.clear()
        _post(credential, provider=provider)
        assert len(calls) <= 1, (credential, provider, calls)


def test_mock_and_local_qa_remain_compatible_for_the_shared_key(
    global_shared_key, all_providers_configured, adapter_spy
):
    """O caller ambíguo continua atendido com Mock e QA local determinística."""
    calls = adapter_spy()

    mock_data = _post(GLOBAL_SHARED_KEY, provider="mock", allow_real_provider=False).json()
    local_data = _post(
        GLOBAL_SHARED_KEY,
        provider="local_qa",
        task_type="qa_report_analysis",
        allow_real_provider=False,
        artifacts=[{"type": "qa_report", "content": "125 passed, 0 failed."}],
    ).json()

    assert mock_data["status"] == "ok"
    assert mock_data["provider_used"] == "mock"
    assert local_data["provider_used"] == "local_qa"
    assert local_data["model"] == "local-qa-v1"
    assert calls == []


# ---------------------------------------------------------------------------
# 16. Contrato público do FinGuard
# ---------------------------------------------------------------------------
def test_finguard_public_contract_is_unchanged(
    global_shared_key, all_providers_configured, adapter_spy
):
    adapter_spy()

    data = _post(GLOBAL_SHARED_KEY, provider="mock", allow_real_provider=False).json()
    frontend_fields = set(AssistantResponsePayload.model_fields)

    assert {"answer", "suggestions", "disclaimer"} <= frontend_fields
    for forbidden in ("identity_strength", "credential_id", "caller_role"):
        assert forbidden not in frontend_fields
    # O contrato de /api/orchestrate mantém as chaves existentes.
    for key in (
        "status",
        "answer",
        "provider_requested",
        "provider_used",
        "model",
        "project_id",
        "warning_codes",
        "audit",
    ):
        assert key in data, key
    assert GLOBAL_SHARED_KEY not in json.dumps(data, ensure_ascii=False)
