from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_mock_chat():
    response = client.post(
        "/api/chat",
        json={
            "message": "Teste",
            "mode": "tecnico",
            "provider": "mock",
            "model": "mock-v1",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["provider"] == "mock"
    assert data["requested_provider"] == "mock"
    assert data["fallback_used"] is False
    assert "Resposta tecnica simulada" in data["answer"]


def test_unknown_provider_falls_back_to_mock():
    response = client.post(
        "/api/chat",
        json={
            "message": "Teste",
            "mode": "tecnico",
            "provider": "inexistente",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["provider"] == "mock"
    assert data["requested_provider"] == "inexistente"
    assert data["fallback_used"] is True
    assert data["error"] is not None


def test_empty_message_validation():
    response = client.post(
        "/api/chat",
        json={
            "message": "",
            "mode": "tecnico",
            "provider": "mock",
        },
    )

    assert response.status_code == 422
