from fastapi.testclient import TestClient

from app.main import app
from app.modules.task_router.service import task_router

client = TestClient(app)


def test_legacy_request_without_task_type_still_works():
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
    assert data["task_type"] == "general_chat"
    assert data["origin_system"] == "pedrocore"
    assert data["task_criticality"] == "low"
    assert data["requires_structured_response"] is False
    assert data["task_warnings"] == []


def test_general_chat_task_type_is_returned():
    response = client.post(
        "/api/chat",
        json={
            "message": "Teste",
            "mode": "tecnico",
            "provider": "mock",
            "task_type": "general_chat",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["task_type"] == "general_chat"
    assert data["task_warnings"] == []


def test_qa_report_analysis_strategy_fields():
    response = client.post(
        "/api/chat",
        json={
            "message": "Analise este relatório",
            "mode": "tecnico",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "context": {"module": "personal-finance"},
            "metadata": {"source": "manual-test"},
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["task_type"] == "qa_report_analysis"
    assert data["origin_system"] == "finguard"
    assert data["requires_structured_response"] is True
    assert data["task_criticality"] == "high"
    assert any("tarefa crítica" in warning for warning in data["task_warnings"])


def test_release_gate_review_fallback_adds_critical_warning():
    response = client.post(
        "/api/chat",
        json={
            "message": "Pode avançar para release?",
            "mode": "tecnico",
            "provider": "inexistente",
            "task_type": "release_gate_review",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["provider"] == "mock"
    assert data["fallback_used"] is True
    assert data["task_type"] == "release_gate_review"
    assert data["task_criticality"] == "critical"
    assert any(
        "Fallback Mock usado em tarefa crítica" in warning
        for warning in data["task_warnings"]
    )


def test_unknown_task_type_returns_warning_without_breaking():
    response = client.post(
        "/api/chat",
        json={
            "message": "Teste",
            "mode": "tecnico",
            "provider": "mock",
            "task_type": "tarefa_que_nao_existe",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["task_type"] == "unknown"
    assert any("task_type desconhecido" in warning for warning in data["task_warnings"])


def test_task_router_normalizes_case_and_whitespace():
    strategy = task_router.resolve("  QA_Report_Analysis  ")

    assert strategy.task_type == "qa_report_analysis"
    assert strategy.requires_structured_response is True
    assert strategy.criticality == "high"
    assert strategy.allow_mock is False


def test_task_router_defaults_to_general_chat():
    for value in (None, "", "   "):
        strategy = task_router.resolve(value)

        assert strategy.task_type == "general_chat"
        assert strategy.criticality == "low"
        assert strategy.allow_mock is True
        assert strategy.warnings == []


def test_providers_endpoint_still_works():
    response = client.get("/api/providers")
    data = response.json()
    names = {provider["name"] for provider in data}

    assert response.status_code == 200
    assert {"mock", "gemini", "openai", "claude", "deepseek", "grok"}.issubset(names)
