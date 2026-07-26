"""Caracterização congelada do modo automático (Etapa 1).

Congela o comportamento que NÃO pode mudar durante a evolução multi-provider:
`provider=auto` continua Gemini-only, Claude/OpenAI configurados não entram no
automático, falha de Gemini vira Mock seguro (nunca outro provider real) e
nenhuma requisição normal executa dois providers reais.

Nenhum teste aqui usa rede, chave real ou smoke real: todo provider real é
substituído por stub/spy determinístico.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.orchestration.service import (
    AUTO_REAL_PROVIDER_CANDIDATES,
    orchestration_service,
)
from app.modules.providers.base import ProviderExecutionError, ProviderResponse
from app.modules.providers.claude_provider import ClaudeProvider
from app.modules.providers.deepseek_provider import DeepSeekProvider
from app.modules.providers.gemini_provider import GeminiProvider
from app.modules.providers.grok_provider import GrokProvider
from app.modules.providers.openai_provider import OpenAIProvider

client = TestClient(app)

FAKE_KEY = "test-characterization-key-never-leak"

REAL_PROVIDER_CLASSES = (
    GeminiProvider,
    OpenAIProvider,
    ClaudeProvider,
    DeepSeekProvider,
    GrokProvider,
)

# Campos que o frontend do FinGuard consome. O contrato público não pode
# ganhar metadados técnicos nesta frente.
FINGUARD_FRONTEND_FIELDS = {"answer", "suggestions", "disclaimer"}

ASSISTANT_PAYLOAD_FIELDS = {
    "answer",
    "suggestions",
    "disclaimer",
    "safety_flags",
    "provider_used",
    "model",
    "audit_id",
    "memory_used",
    "evaluation",
    "warnings",
}


@pytest.fixture
def real_provider_spy(monkeypatch):
    """Substitui TODO provider real por um spy: registra e nunca usa rede.

    Providers em `failing` levantam erro de execução; os demais devolvem uma
    resposta determinística.
    """
    calls: list[str] = []

    def install(failing: set[str] | None = None):
        failing = failing or set()

        def make(provider_name: str):
            async def stub(self, message, mode, model=None, system_prompt=None):
                calls.append(provider_name)
                if provider_name in failing:
                    raise ProviderExecutionError(
                        f"Falha simulada e determinística do provider {provider_name}."
                    )
                return ProviderResponse(
                    answer=f"Resposta stubada de {provider_name}.",
                    provider=provider_name,
                    model=model or f"{provider_name}-stub-v1",
                )

            return stub

        for cls in REAL_PROVIDER_CLASSES:
            monkeypatch.setattr(cls, "generate_response", make(cls.name))
        return calls

    install.calls = calls
    return install


def _payload(**overrides) -> dict:
    payload = {
        "message": "Pergunta segura de caracterização.",
        "provider": "auto",
        "task_type": "assistant_chat",
        "origin_system": "finguard",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    return payload


def _configure(monkeypatch, **keys) -> None:
    defaults = {
        "gemini_api_key": "",
        "anthropic_api_key": "",
        "openai_api_key": "",
        "deepseek_api_key": "",
        "xai_api_key": "",
    }
    defaults.update(keys)
    for attribute, value in defaults.items():
        monkeypatch.setattr(settings, attribute, value)


def test_auto_candidate_list_is_frozen_as_gemini_only():
    assert AUTO_REAL_PROVIDER_CANDIDATES == ("gemini",)


def test_auto_with_gemini_configured_uses_gemini(monkeypatch, real_provider_spy):
    _configure(monkeypatch, gemini_api_key=FAKE_KEY)
    calls = real_provider_spy()

    data = client.post("/api/orchestrate", json=_payload()).json()

    assert data["provider_used"] == "gemini"
    assert data["fallback_used"] is False
    assert calls == ["gemini"]


def test_auto_with_gemini_and_claude_configured_never_calls_claude(
    monkeypatch, real_provider_spy
):
    _configure(monkeypatch, gemini_api_key=FAKE_KEY, anthropic_api_key=FAKE_KEY)
    calls = real_provider_spy()

    data = client.post("/api/orchestrate", json=_payload()).json()

    assert data["provider_used"] == "gemini"
    assert calls == ["gemini"]
    assert "claude" not in calls


def test_auto_with_openai_configured_never_calls_openai(monkeypatch, real_provider_spy):
    _configure(monkeypatch, gemini_api_key=FAKE_KEY, openai_api_key=FAKE_KEY)
    calls = real_provider_spy()

    data = client.post("/api/orchestrate", json=_payload()).json()

    assert data["provider_used"] == "gemini"
    assert "openai" not in calls


def test_gemini_failure_falls_back_to_safe_mock_and_never_to_claude(
    monkeypatch, real_provider_spy
):
    _configure(monkeypatch, gemini_api_key=FAKE_KEY, anthropic_api_key=FAKE_KEY)
    calls = real_provider_spy(failing={"gemini"})

    data = client.post("/api/orchestrate", json=_payload()).json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert calls == ["gemini"]
    assert "claude" not in calls


def test_only_claude_configured_with_auto_results_in_mock(monkeypatch, real_provider_spy):
    _configure(monkeypatch, anthropic_api_key=FAKE_KEY)
    calls = real_provider_spy()

    data = client.post("/api/orchestrate", json=_payload()).json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert data["error_code"] == codes.PROVIDER_REAL_UNAVAILABLE
    assert calls == []


def test_only_openai_configured_with_auto_results_in_mock(monkeypatch, real_provider_spy):
    _configure(monkeypatch, openai_api_key=FAKE_KEY)
    calls = real_provider_spy()

    data = client.post("/api/orchestrate", json=_payload()).json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert calls == []


def test_no_normal_request_calls_two_real_providers(monkeypatch, real_provider_spy):
    _configure(
        monkeypatch,
        gemini_api_key=FAKE_KEY,
        anthropic_api_key=FAKE_KEY,
        openai_api_key=FAKE_KEY,
        deepseek_api_key=FAKE_KEY,
        xai_api_key=FAKE_KEY,
    )
    calls = real_provider_spy(failing={"gemini"})

    for provider in ("auto", "gemini", "mock", "local_qa"):
        calls.clear()
        client.post("/api/orchestrate", json=_payload(provider=provider))
        assert len(calls) <= 1, (provider, calls)


def test_safe_mode_still_blocks_real_provider_without_consent(
    monkeypatch, real_provider_spy
):
    _configure(monkeypatch, gemini_api_key=FAKE_KEY)
    calls = real_provider_spy()

    data = client.post(
        "/api/orchestrate", json=_payload(allow_real_provider=False)
    ).json()

    assert data["safe_mode_blocked"] is True
    assert data["provider_used"] == "mock"
    assert codes.PROVIDER_REAL_BLOCKED in data["warning_codes"]
    assert calls == []


def test_mock_provider_still_works(real_provider_spy):
    calls = real_provider_spy()

    data = client.post(
        "/api/orchestrate", json=_payload(provider="mock", allow_real_provider=False)
    ).json()

    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is False
    assert calls == []


def test_local_qa_still_works(real_provider_spy):
    calls = real_provider_spy()

    data = client.post(
        "/api/orchestrate",
        json=_payload(
            provider="local_qa",
            task_type="qa_report_analysis",
            allow_real_provider=False,
            artifacts=[{"type": "qa_report", "content": "120 passed, 0 failed."}],
        ),
    ).json()

    assert data["provider_used"] == "local_qa"
    assert data["model"] == "local-qa-v1"
    assert calls == []


def test_explicit_technical_selection_remains_compatible(monkeypatch, real_provider_spy):
    _configure(monkeypatch, gemini_api_key=FAKE_KEY)
    calls = real_provider_spy()

    data = client.post("/api/orchestrate", json=_payload(provider="gemini")).json()

    assert data["provider_requested"] == "gemini"
    assert data["provider_used"] == "gemini"
    assert calls == ["gemini"]


def test_orchestrate_contract_keys_are_preserved(real_provider_spy):
    real_provider_spy()

    data = client.post(
        "/api/orchestrate", json=_payload(provider="mock", allow_real_provider=False)
    ).json()

    required = {
        "status",
        "answer",
        "task_type",
        "origin_system",
        "provider_requested",
        "provider_used",
        "model",
        "mode",
        "fallback_used",
        "safe_mode_blocked",
        "allow_real_provider",
        "warning_codes",
        "warnings",
        "task_warnings",
        "error_code",
        "blocked_reason",
        "project_id",
        "task_allowed_for_project",
        "artifact_count",
        "artifact_types",
        "artifact_warnings",
        "qa",
        "release_gate",
        "audit",
        "memory_used",
    }
    assert required <= set(data)


def test_finguard_frontend_payload_gains_no_technical_metadata(real_provider_spy):
    real_provider_spy()

    outcome = asyncio.run(
        orchestration_service.execute(
            ChatRequest(
                message="Como está o meu projeto?",
                provider="mock",
                task_type="assistant_chat",
                origin_system="finguard",
            )
        )
    )
    payload = orchestration_service.build_assistant_payload(outcome)
    fields = set(payload.model_dump().keys())

    assert FINGUARD_FRONTEND_FIELDS <= fields
    # Congela a projeção: nenhum campo técnico novo foi adicionado nesta frente.
    assert fields == ASSISTANT_PAYLOAD_FIELDS
