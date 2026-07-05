from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REAL_PROVIDERS = ["gemini", "openai", "claude", "deepseek", "grok"]

CLEAN_SUCCESS = "All tests passed. 0 failed. Build successful."


def test_real_provider_blocked_by_default():
    response = client.post(
        "/api/chat",
        json={"message": "Teste", "provider": "gemini"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["requested_provider"] == "gemini"
    assert data["provider"] == "mock"
    assert data["fallback_used"] is True
    assert data["safe_mode_blocked"] is True
    assert "PROVIDER_REAL_BLOCKED" in data["warning_codes"]
    assert data["error_code"] == "PROVIDER_REAL_BLOCKED"


def test_allow_real_provider_absent_means_false():
    response = client.post(
        "/api/chat",
        json={"message": "Teste", "provider": "openai"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["safe_mode_blocked"] is True
    assert data["fallback_used"] is True


def test_all_real_providers_are_blocked_by_default():
    for provider in REAL_PROVIDERS:
        response = client.post(
            "/api/chat",
            json={"message": "Teste", "provider": provider},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["safe_mode_blocked"] is True, f"provider nao bloqueado: {provider}"
        assert data["provider"] == "mock"
        assert "PROVIDER_REAL_BLOCKED" in data["warning_codes"]


def test_mock_provider_is_not_blocked_by_safe_mode():
    response = client.post(
        "/api/chat",
        json={"message": "Teste", "provider": "mock"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["safe_mode_blocked"] is False
    assert data["fallback_used"] is False


def test_local_provider_is_not_blocked_by_safe_mode():
    response = client.post(
        "/api/chat",
        json={"message": "Teste", "provider": "local_qa"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["safe_mode_blocked"] is False
    assert data["provider"] == "local_qa"
    assert data["model"] == "local-qa-v1"


def test_release_gate_with_blocked_real_provider_cannot_advance():
    response = client.post(
        "/api/chat",
        json={
            "message": "Pode liberar?",
            "provider": "gemini",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": CLEAN_SUCCESS}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["safe_mode_blocked"] is True
    assert data["qa_skeleton"]["can_advance"] is False
    assert "PROVIDER_REAL_BLOCKED" in data["warning_codes"]
    assert "RELEASE_GATE_BLOCKED" in data["warning_codes"]
    assert data["status"] == "blocked"
