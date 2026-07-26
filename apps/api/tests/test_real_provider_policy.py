import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.contracts import codes
from app.modules.providers.base import ProviderResponse
from app.modules.providers.gemini_provider import GeminiProvider

client = TestClient(app)

AUTH_ENV_VAR = "PEDROCORE_INTERNAL_API_KEY"
AUTH_HEADER = "X-PedroCore-Api-Key"
TEST_KEY = "test-gemini-key-never-leak"

# Provider real para o projeto FinGuard exige credencial REGISTRADA que
# vincule a credencial ao projeto: chave global compartilhada não basta.
FINGUARD_CONSUMER_CREDENTIAL = "finguard-consumer-credencial-sintetica"
FINGUARD_TOOL_CREDENTIAL = "finguard-tool-credencial-sintetica"


def _register_finguard_credentials(monkeypatch) -> None:
    monkeypatch.setenv(
        FLAG_CALLER_REGISTRY,
        json.dumps(
            [
                {
                    "credential_id": "finguard-consumer",
                    "api_key": FINGUARD_CONSUMER_CREDENTIAL,
                    "project_id": "finguard",
                    "role": "common_consumer",
                    "environment": "development",
                    "allowed_origins": ["finguard"],
                },
                {
                    "credential_id": "finguard-tool",
                    "api_key": FINGUARD_TOOL_CREDENTIAL,
                    "project_id": "finguard",
                    "role": "technical_tool",
                    "environment": "development",
                    "allowed_origins": ["finguard"],
                },
            ]
        ),
    )


def _payload(provider: str, allow_real_provider: bool = False) -> dict:
    return {
        "origin_system": "finguard",
        "project_id": "finguard",
        "task_type": "finance_advice",
        "message": "Como devo organizar uma divida sem executar acao financeira?",
        "provider": provider,
        "allow_real_provider": allow_real_provider,
        "allow_local_model": False,
        "context_from_memory": False,
        "context": {"environment": "personal", "objective": "debts"},
    }


def test_mock_provider_does_not_call_gemini(monkeypatch, real_provider_guard):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)
    response = client.post("/api/orchestrate", json=_payload("mock"))
    data = response.json()

    assert response.status_code == 200
    assert data["provider_requested"] == "mock"
    assert data["provider_used"] == "mock"
    assert data["allow_real_provider"] is False
    assert real_provider_guard == []


def test_auto_without_real_authorization_uses_safe_mock(monkeypatch, real_provider_guard):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)
    response = client.post("/api/orchestrate", json=_payload("auto"))
    data = response.json()

    assert response.status_code == 200
    assert data["provider_requested"] == "auto"
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert data["safe_mode_blocked"] is True
    assert codes.PROVIDER_REAL_BLOCKED in data["warning_codes"]
    assert real_provider_guard == []


def test_gemini_without_real_authorization_is_blocked(monkeypatch, real_provider_guard):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)
    response = client.post("/api/orchestrate", json=_payload("gemini"))
    data = response.json()

    assert response.status_code == 200
    assert data["provider_requested"] == "gemini"
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert data["safe_mode_blocked"] is True
    assert data["error_code"] == codes.PROVIDER_REAL_BLOCKED
    assert real_provider_guard == []


def test_auto_with_real_authorization_chooses_gemini_stub(monkeypatch, real_provider_guard):
    """FinGuard com credencial REGISTRADA alcança Gemini via provider=auto.

    A chave global compartilhada não serve mais para isso: só uma credencial
    que vincula inequivocamente o caller ao projeto estabelece identidade.
    """
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)
    _register_finguard_credentials(monkeypatch)
    monkeypatch.setattr(settings, "gemini_api_key", TEST_KEY)
    calls: list[str] = []

    async def fake_generate(self, message, mode, model=None, system_prompt=None):
        calls.append(self.name)
        return ProviderResponse(
            answer="Resposta Gemini stubada e conservadora.",
            provider="gemini",
            model=model or "gemini-stub-v1",
        )

    monkeypatch.setattr(GeminiProvider, "generate_response", fake_generate)

    response = client.post(
        "/api/orchestrate",
        json=_payload("auto", allow_real_provider=True),
        headers={AUTH_HEADER: FINGUARD_CONSUMER_CREDENTIAL},
    )
    data = response.json()
    dumped = json.dumps(data, ensure_ascii=False)

    assert response.status_code == 200
    assert data["provider_requested"] == "auto"
    assert data["provider_used"] == "gemini"
    # Etapa 3: o modelo é derivado internamente pelo PedroCore (default
    # declarado do Gemini), não pelo adapter nem pelo payload.
    assert data["model"] == settings.gemini_model
    assert data["audit"]["model_requested"] is None
    assert data["audit"]["model_selected"] == settings.gemini_model
    assert data["fallback_used"] is False
    assert data["safe_mode_blocked"] is False
    assert calls == ["gemini"]
    assert real_provider_guard == []
    assert TEST_KEY not in dumped


def test_gemini_with_real_authorization_uses_gemini_stub(monkeypatch, real_provider_guard):
    """Seleção explícita continua possível para credencial técnica REGISTRADA."""
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)
    _register_finguard_credentials(monkeypatch)
    monkeypatch.setattr(settings, "gemini_api_key", TEST_KEY)
    calls: list[str] = []

    async def fake_generate(self, message, mode, model=None, system_prompt=None):
        calls.append(self.name)
        return ProviderResponse(
            answer="Gemini direto via PedroCore stubado.",
            provider="gemini",
            model=model or "gemini-stub-v1",
        )

    monkeypatch.setattr(GeminiProvider, "generate_response", fake_generate)

    response = client.post(
        "/api/orchestrate",
        json=_payload("gemini", allow_real_provider=True),
        headers={AUTH_HEADER: FINGUARD_TOOL_CREDENTIAL},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["provider_requested"] == "gemini"
    assert data["provider_used"] == "gemini"
    # Sem modelo no payload, o PedroCore seleciona o default do provider.
    assert data["model"] == settings.gemini_model
    assert data["audit"]["model_source"] == "provider_default"
    assert data["fallback_used"] is False
    assert calls == ["gemini"]
    assert real_provider_guard == []
    assert TEST_KEY not in json.dumps(data, ensure_ascii=False)


def test_real_authorization_without_gemini_key_falls_back_controlled(monkeypatch, real_provider_guard):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", "")
    response = client.post("/api/orchestrate", json=_payload("auto", allow_real_provider=True))
    data = response.json()

    assert response.status_code == 200
    assert data["provider_requested"] == "auto"
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert data["error_code"] == codes.PROVIDER_REAL_UNAVAILABLE
    assert codes.PROVIDER_REAL_UNAVAILABLE in data["warning_codes"]
    assert real_provider_guard == []


def test_local_qa_remains_available(monkeypatch, real_provider_guard):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)
    response = client.post("/api/orchestrate", json=_payload("local_qa"))
    data = response.json()

    assert response.status_code == 200
    assert data["provider_used"] == "local_qa"
    assert data["model"] == "local-qa-v1"
    assert real_provider_guard == []


def test_orchestrate_still_requires_internal_api_key(monkeypatch):
    monkeypatch.setenv(AUTH_ENV_VAR, "internal-test-key")
    response = client.post("/api/orchestrate", json=_payload("mock"))
    data = response.json()

    assert response.status_code == 401
    assert data["error_code"] == codes.INTERNAL_AUTH_MISSING
    assert "internal-test-key" not in json.dumps(data, ensure_ascii=False)

    allowed = client.post(
        "/api/orchestrate",
        json=_payload("mock"),
        headers={AUTH_HEADER: "internal-test-key"},
    )
    assert allowed.status_code == 200
