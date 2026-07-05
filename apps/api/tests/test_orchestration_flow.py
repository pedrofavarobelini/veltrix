from fastapi.testclient import TestClient

from app.main import app
from app.modules.chat.schemas import ChatRequest
from app.modules.providers.registry import provider_registry

client = TestClient(app)


def test_legacy_request_returns_orchestration_defaults():
    response = client.post(
        "/api/chat",
        json={
            "message": "Explique FastAPI",
            "mode": "tecnico",
            "provider": "mock",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["provider"] == "mock"
    assert data["fallback_used"] is False
    assert data["project_id"] == "pedrocore"
    assert data["project_read_only"] is True
    assert data["project_can_execute_commands"] is False
    assert data["project_can_write_files"] is False
    assert data["response_style"] == "free_text"
    assert data["task_warnings"] == []


def test_finguard_origin_returns_project_metadata():
    response = client.post(
        "/api/chat",
        json={
            "message": "Resuma este artefato",
            "mode": "tecnico",
            "provider": "mock",
            "task_type": "artifact_summary",
            "origin_system": "finguard",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["origin_system"] == "finguard"
    assert data["project_id"] == "finguard"
    assert data["project_read_only"] is True
    assert data["project_can_execute_commands"] is False
    assert data["project_can_write_files"] is False


def test_unknown_origin_system_returns_warning():
    response = client.post(
        "/api/chat",
        json={
            "message": "Teste",
            "mode": "tecnico",
            "provider": "mock",
            "origin_system": "sistema_que_nao_existe",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["project_id"] == "unknown"
    assert any("desconhecido" in warning for warning in data["task_warnings"])


def test_release_gate_review_fallback_keeps_critical_warning_and_audit():
    response = client.post(
        "/api/chat",
        json={
            "message": "Pode avançar para release?",
            "mode": "tecnico",
            "provider": "inexistente",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["provider"] == "mock"
    assert data["fallback_used"] is True
    assert data["task_criticality"] == "critical"
    assert data["project_id"] == "finguard"
    assert any(
        "Fallback Mock usado em tarefa crítica" in warning
        for warning in data["task_warnings"]
    )
    assert data["audit_id"]
    assert data["audit_timestamp"]


def test_critical_task_keeps_requires_structured_response():
    response = client.post(
        "/api/chat",
        json={
            "message": "Analise este relatório",
            "mode": "tecnico",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["requires_structured_response"] is True
    assert data["response_style"] == "qa_structured_planned"


def test_response_contains_audit_metadata():
    first = client.post(
        "/api/chat",
        json={"message": "Teste", "mode": "tecnico", "provider": "mock"},
    ).json()
    second = client.post(
        "/api/chat",
        json={"message": "Teste", "mode": "tecnico", "provider": "mock"},
    ).json()

    assert first["audit_id"]
    assert first["audit_timestamp"]
    assert first["audit_id"] != second["audit_id"]


def test_providers_endpoint_still_works():
    response = client.get("/api/providers")
    data = response.json()
    names = {provider["name"] for provider in data}

    assert response.status_code == 200
    assert {"mock", "gemini", "openai", "claude", "deepseek", "grok"}.issubset(names)


def test_suite_uses_only_safe_providers():
    assert ChatRequest(message="x").provider == "mock"

    mock = provider_registry.get("mock")
    assert mock is not None
    assert mock.real_provider is False
    assert mock.is_configured is True
