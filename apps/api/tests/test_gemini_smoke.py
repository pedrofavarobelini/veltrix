import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.observability.gemini_smoke import SYNTHETIC_PAYLOAD
from app.modules.observability.service import FLAG_ENABLED, observability_service
from app.modules.providers.base import BaseAIProvider, ProviderResponse
from app.modules.providers.registry import provider_registry
from app.modules.real_features import service as real_features

client = TestClient(app)


class FakeGemini(BaseAIProvider):
    name = "gemini"
    label = "Gemini fake seguro"
    default_model = "gemini-fake-v1"
    real_provider = True

    def __init__(self, *, configured: bool = True, fail: bool = False) -> None:
        self.configured = configured
        self.fail = fail
        self.calls = 0

    @property
    def is_configured(self) -> bool:
        return self.configured

    async def generate_response(self, **_kwargs) -> ProviderResponse:
        self.calls += 1
        if self.fail:
            raise RuntimeError("falha externa token=segredo-nao-vazar")
        return ProviderResponse(
            answer="OK",
            provider=self.name,
            model=self.default_model,
        )


@pytest.fixture(autouse=True)
def safe_smoke_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.delenv(real_features.FLAG_RUN_REAL_PROVIDER_TESTS, raising=False)
    monkeypatch.delenv(real_features.FLAG_RUN_REAL_GEMINI_TESTS, raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    observability_service.reset()
    yield
    observability_service.reset()


def _payload(**overrides):
    payload = {
        "synthetic_payload": SYNTHETIC_PAYLOAD,
        "confirm_network": True,
        "confirm_possible_cost": True,
        "confirm_key_not_compromised": True,
    }
    payload.update(overrides)
    return payload


def _enable_flags(monkeypatch):
    monkeypatch.setenv(real_features.FLAG_RUN_REAL_PROVIDER_TESTS, "true")
    monkeypatch.setenv(real_features.FLAG_RUN_REAL_GEMINI_TESTS, "true")


def _latest_detail() -> dict:
    listing = client.get("/api/observability/executions").json()["items"]
    assert listing
    return client.get(
        f"/api/observability/executions/{listing[0]['execution_id']}"
    ).json()


def test_missing_key_is_external_credential_block_without_call(monkeypatch):
    fake = FakeGemini()
    monkeypatch.setitem(provider_registry._providers, "gemini", fake)
    _enable_flags(monkeypatch)

    response = client.post("/api/observability/gemini-smoke", json=_payload())
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == "blocked"
    assert data["executed"] is False
    assert data["call_count"] == 0
    assert "Credencial externa" in data["reason"]
    assert fake.calls == 0


def test_both_optin_flags_are_required(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    monkeypatch.setenv(real_features.FLAG_RUN_REAL_PROVIDER_TESTS, "true")
    fake = FakeGemini()
    monkeypatch.setitem(provider_registry._providers, "gemini", fake)

    data = client.post("/api/observability/gemini-smoke", json=_payload()).json()
    assert data["status"] == "blocked"
    assert "duas flags" in data["reason"]
    assert fake.calls == 0


def test_production_is_blocked_before_provider_call(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    _enable_flags(monkeypatch)
    fake = FakeGemini()
    monkeypatch.setitem(provider_registry._providers, "gemini", fake)

    data = client.post("/api/observability/gemini-smoke", json=_payload()).json()
    assert data["status"] == "blocked"
    assert "produção" in data["reason"]
    assert fake.calls == 0


def test_inadequate_payload_and_missing_confirmation_are_blocked(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    _enable_flags(monkeypatch)
    fake = FakeGemini()
    monkeypatch.setitem(provider_registry._providers, "gemini", fake)

    wrong = client.post(
        "/api/observability/gemini-smoke",
        json=_payload(synthetic_payload="conteudo-do-usuario"),
    ).json()
    unconfirmed = client.post(
        "/api/observability/gemini-smoke",
        json=_payload(confirm_possible_cost=False),
    ).json()
    assert wrong["status"] == "blocked"
    assert unconfirmed["status"] == "blocked"
    assert fake.calls == 0


def test_provider_unavailable_is_blocked_without_call(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    _enable_flags(monkeypatch)
    fake = FakeGemini(configured=False)
    monkeypatch.setitem(provider_registry._providers, "gemini", fake)

    data = client.post("/api/observability/gemini-smoke", json=_payload()).json()
    assert data["status"] == "blocked"
    assert "indisponível" in data["reason"]
    assert fake.calls == 0


def test_safe_fake_execution_is_exactly_one_call_and_sanitized(monkeypatch):
    key = "fake-key-never-leak"
    monkeypatch.setattr(settings, "gemini_api_key", key)
    _enable_flags(monkeypatch)
    fake = FakeGemini()
    monkeypatch.setitem(provider_registry._providers, "gemini", fake)

    response = client.post("/api/observability/gemini-smoke", json=_payload())
    data = response.json()
    assert data["status"] == "ok"
    assert data["executed"] is True
    assert data["call_count"] == 1
    assert fake.calls == 1
    assert key not in json.dumps(data)

    detail = _latest_detail()
    assert detail["task"] == "gemini_real_smoke"
    assert detail["provider_attempts"] == [
        {"provider": "gemini", "result": "success", "detail": None}
    ]
    assert key not in json.dumps(detail)


def test_provider_failure_returns_sanitized_visible_fallback(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    _enable_flags(monkeypatch)
    fake = FakeGemini(fail=True)
    monkeypatch.setitem(provider_registry._providers, "gemini", fake)

    data = client.post("/api/observability/gemini-smoke", json=_payload()).json()
    assert data["status"] == "fallback"
    assert data["executed"] is True
    assert data["call_count"] == 1
    assert data["fallback"] is True
    assert "segredo-nao-vazar" not in json.dumps(data)
    assert fake.calls == 1

    detail = _latest_detail()
    assert detail["provider_attempts"][-1]["result"] == "fallback_success"
    assert "segredo-nao-vazar" not in json.dumps(detail)
