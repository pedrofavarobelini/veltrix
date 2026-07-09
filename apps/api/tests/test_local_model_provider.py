import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.providers.local_model_provider import (
    FLAG_ENABLE_LOCAL_MODEL,
    FLAG_LOCAL_MODEL_BACKEND,
    FLAG_LOCAL_MODEL_ENDPOINT,
    LocalModelTransport,
    local_model_provider,
    local_model_ready,
)
from app.modules.qa_response.service import RELEASE_GATE_TRUSTED_PROVIDERS

client = TestClient(app)

CLEAN_QA_EVIDENCE = "257 passed, 6 skipped. Build successful. 0 failed."


class FakeTransport(LocalModelTransport):
    def __init__(self, answer: str = "Resposta do modelo local fake."):
        self.answer = answer
        self.calls: list[dict] = []

    async def generate(self, *, endpoint, model, prompt, timeout_seconds) -> str:
        self.calls.append(
            {"endpoint": endpoint, "model": model, "timeout": timeout_seconds}
        )
        return self.answer


@pytest.fixture(autouse=True)
def reset_transport(monkeypatch):
    monkeypatch.delenv(FLAG_ENABLE_LOCAL_MODEL, raising=False)
    monkeypatch.delenv(FLAG_LOCAL_MODEL_BACKEND, raising=False)
    local_model_provider.set_transport(None)
    yield
    local_model_provider.set_transport(None)


def _enable(monkeypatch):
    monkeypatch.setenv(FLAG_ENABLE_LOCAL_MODEL, "true")
    monkeypatch.setenv(FLAG_LOCAL_MODEL_BACKEND, "ollama")
    monkeypatch.setenv(FLAG_LOCAL_MODEL_ENDPOINT, "http://127.0.0.1:11434")


def test_local_model_disabled_by_default():
    assert local_model_ready() is False
    assert local_model_provider.is_configured is False

    providers = {p["name"]: p for p in client.get("/api/providers").json()}
    assert "local_model" in providers
    assert providers["local_model"]["configured"] is False
    assert providers["local_model"]["real_provider"] is False


def test_local_model_without_authorization_falls_back_to_mock():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Oi",
            "provider": "local_model",
            "task_type": "local_model_chat",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert "LOCAL_MODEL_NOT_AUTHORIZED" in data["warning_codes"]
    assert data["safe_mode_blocked"] is False


def test_local_model_with_flag_off_does_not_call_network():
    transport = FakeTransport()
    local_model_provider.set_transport(transport)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Oi",
            "provider": "local_model",
            "task_type": "local_model_chat",
            "allow_local_model": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["provider_used"] == "mock"
    assert "LOCAL_MODEL_DISABLED" in data["warning_codes"]
    assert transport.calls == []


def test_local_model_with_fake_transport_returns_normalized_response(monkeypatch):
    _enable(monkeypatch)
    transport = FakeTransport(answer="Resposta gerada localmente.")
    local_model_provider.set_transport(transport)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Oi",
            "provider": "local_model",
            "task_type": "local_model_chat",
            "allow_local_model": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["provider_used"] == "local_model"
    assert data["fallback_used"] is False
    assert data["answer"] == "Resposta gerada localmente."
    assert "LOCAL_MODEL_USED" in data["warning_codes"]
    assert data["allow_real_provider"] is False
    assert len(transport.calls) == 1


def test_local_model_enabled_without_transport_falls_back(monkeypatch):
    _enable(monkeypatch)
    local_model_provider.set_transport(None)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Oi",
            "provider": "local_model",
            "task_type": "local_model_chat",
            "allow_local_model": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert "LOCAL_MODEL_TRANSPORT_UNAVAILABLE" in data["warning_codes"]


def test_local_model_blocked_for_release_gate(monkeypatch):
    _enable(monkeypatch)
    transport = FakeTransport(answer=CLEAN_QA_EVIDENCE)
    local_model_provider.set_transport(transport)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode avançar?",
            "provider": "local_model",
            "task_type": "release_gate_review",
            "allow_local_model": True,
            "artifacts": [
                {"type": "qa_report", "name": "qa.txt", "content": CLEAN_QA_EVIDENCE}
            ],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert "LOCAL_MODEL_TASK_BLOCKED" in data["warning_codes"]
    assert transport.calls == []
    assert data["release_gate"] is not None
    assert data["release_gate"]["can_advance"] is False


def test_local_model_never_trusted_for_release_gate():
    assert "local_model" not in RELEASE_GATE_TRUSTED_PROVIDERS
    assert RELEASE_GATE_TRUSTED_PROVIDERS == {"local_qa"}


def test_local_model_does_not_require_allow_real_provider(monkeypatch):
    _enable(monkeypatch)
    local_model_provider.set_transport(FakeTransport())

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Oi",
            "provider": "local_model",
            "task_type": "local_model_chat",
            "allow_local_model": True,
            "allow_real_provider": False,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["provider_used"] == "local_model"
    assert data["safe_mode_blocked"] is False
