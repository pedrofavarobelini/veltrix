"""Verdade sobre quem respondeu no chat interativo do Veltrix.

Cenário reproduzido: Gemini configurado, homologado, autorizado e explicitamente
escolhido pelo usuário; o provider falha (429, indisponibilidade, timeout) e o
pipeline responde com o Mock. A interface mostrava "Gemini" enquanto exibia uma
resposta genérica do Mock — a falha ficava invisível.

Nenhuma chamada externa: `GeminiProvider.generate_response` é substituído.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.orchestration.service import (
    GENERAL_FALLBACK_ANSWER,
    GENERAL_NO_MOCK_FALLBACK_ANSWER,
    SAFE_FALLBACK_ANSWER,
)
from app.modules.providers.base import ProviderExecutionError, ProviderResponse
from app.modules.providers.gemini_provider import GeminiProvider

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
FINGUARD_KEY = "finguard-provider-truth-registered"
SHARED_KEY = "shared-key-provider-truth"
FAKE_PROVIDER_KEY = "provider-truth-synthetic-never-real"

FINGUARD_REGISTRY = json.dumps(
    [
        {
            "credential_id": "finguard-provider-truth",
            "api_key": FINGUARD_KEY,
            "project_id": "finguard",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["finguard"],
        }
    ]
)

SIMPLE_QUESTION = "Me fale o que foi feito recentemente no sistema."


class GeminiSpy:
    """Conta as chamadas que de fato chegariam ao adapter."""

    def __init__(self, outcome=None) -> None:
        self.outcome = outcome
        self.calls = 0

    def install(self, monkeypatch) -> "GeminiSpy":
        async def fake(
            provider_self,
            message,
            mode,
            model,
            system_prompt=None,
            output_budget=None,
            transport_timeout_ms=None,
        ):
            del provider_self, message, mode, system_prompt
            self.calls += 1
            if isinstance(self.outcome, BaseException):
                raise self.outcome
            return ProviderResponse(
                answer="Resposta real sintética do Gemini.",
                provider="gemini",
                model=model,
                finish_reason="STOP",
                output_budget=output_budget,
                transport_timeout_ms=transport_timeout_ms,
            )

        monkeypatch.setattr(GeminiProvider, "generate_response", fake)
        return self


@pytest.fixture
def local_operator(monkeypatch):
    """Operador local do próprio Veltrix — exatamente o que a interface é."""
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)


def _chat(**overrides):
    payload = {
        "message": SIMPLE_QUESTION,
        "mode": "tecnico",
        "provider": "gemini",
        "model": "gemini-3.5-flash",
        "allow_real_provider": True,
    }
    payload.update(overrides)
    return client.post("/api/chat", json=payload)


# ----------------------------------------------------- A) sem consentimento


def test_real_provider_without_consent_never_reaches_the_adapter(
    local_operator, monkeypatch
):
    spy = GeminiSpy().install(monkeypatch)

    data = _chat(allow_real_provider=False).json()

    assert spy.calls == 0
    assert data["provider"] == "mock"
    assert data["safe_mode_blocked"] is True


# --------------------------------------------- B/C) autorizado e bem-sucedido


def test_authorized_local_operator_actually_reaches_gemini(local_operator, monkeypatch):
    spy = GeminiSpy().install(monkeypatch)

    data = _chat().json()

    assert spy.calls == 1
    assert data["requested_provider"] == "gemini"
    assert data["provider"] == "gemini"
    assert data["model"] == "gemini-3.5-flash"
    assert data["fallback_used"] is False
    assert data["answer"] == "Resposta real sintética do Gemini."


# ------------------------------------------------------- D) falha não mente


def test_gemini_failure_is_not_disguised_as_a_mock_answer(local_operator, monkeypatch):
    """Com o opt-out do contrato, a falha volta como falha — nunca como resposta."""
    spy = GeminiSpy(ProviderExecutionError("429 RESOURCE_EXHAUSTED")).install(
        monkeypatch
    )

    data = _chat(allow_mock_fallback=False).json()

    assert spy.calls == 1
    assert data["requested_provider"] == "gemini"
    # `none` é o estado honesto: ninguém respondeu.
    assert data["provider"] == "none"
    assert data["model"] == "none"
    assert data["fallback_used"] is False
    assert data["status"] == "blocked"
    assert data["answer"] == GENERAL_NO_MOCK_FALLBACK_ANSWER


def test_default_contract_still_degrades_to_mock_for_integrated_consumers(
    local_operator, monkeypatch
):
    """O default do contrato NÃO mudou: consumers integrados seguem protegidos."""
    GeminiSpy(ProviderExecutionError("429 RESOURCE_EXHAUSTED")).install(monkeypatch)

    data = _chat().json()

    assert data["provider"] == "mock"
    assert data["fallback_used"] is True


# ------------------------------------- H) chat geral sem disclaimer financeiro


def test_general_chat_fallback_has_no_financial_disclaimer(local_operator, monkeypatch):
    GeminiSpy(ProviderExecutionError("indisponivel")).install(monkeypatch)

    data = _chat().json()

    assert data["answer"] == GENERAL_FALLBACK_ANSWER
    assert "financeira" not in data["answer"]
    assert "seus dados" not in data["answer"]


def test_general_chat_blocked_answer_has_no_financial_disclaimer(
    local_operator, monkeypatch
):
    GeminiSpy(ProviderExecutionError("indisponivel")).install(monkeypatch)

    data = _chat(allow_mock_fallback=False).json()

    assert "financeira" not in data["answer"]


def test_finguard_keeps_its_financial_disclaimer(monkeypatch):
    """O disclaimer financeiro continua onde ele faz sentido."""
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, FINGUARD_REGISTRY)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)
    GeminiSpy(ProviderExecutionError("indisponivel")).install(monkeypatch)

    response = client.post(
        "/api/chat",
        json={
            "message": "Como me organizo financeiramente?",
            "mode": "tecnico",
            "provider": "auto",
            "task_type": "assistant_chat",
            "origin_system": "finguard",
            "allow_real_provider": True,
        },
        headers={AUTH_HEADER: FINGUARD_KEY},
    )
    data = response.json()

    assert data["provider"] == "mock"
    assert data["answer"] == SAFE_FALLBACK_ANSWER
    assert "ação financeira" in data["answer"]


# --------------------------------------- G) caller externo ambíguo sem ganho


def test_ambiguous_external_caller_gains_no_real_provider(monkeypatch):
    """Credencial compartilhada não vira privilégio, nem com o opt-out do chat."""
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, SHARED_KEY)
    monkeypatch.setattr(settings, "gemini_api_key", FAKE_PROVIDER_KEY)
    spy = GeminiSpy().install(monkeypatch)

    response = client.post(
        "/api/chat",
        json={
            "message": SIMPLE_QUESTION,
            "mode": "tecnico",
            "provider": "gemini",
            "model": "gemini-3.5-flash",
            "origin_system": "finguard",
            "allow_real_provider": True,
            "allow_mock_fallback": False,
        },
        headers={AUTH_HEADER: SHARED_KEY},
    )
    data = response.json()

    assert spy.calls == 0
    assert data["provider"] != "gemini"
