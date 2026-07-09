"""Policy Enforcement negativo (PEDROCORE-QA-SAFETY-HARDENING-01).

Prova que o bloqueio de policy acontece ANTES de qualquer provider ser
executado, que payloads inválidos/maliciosos falham de forma controlada
(sem stack trace) e que o disclaimer de finance_advice é inquebrável.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.providers.registry import provider_registry
from app.modules.real_features.service import FLAG_ENFORCE_PROJECT_POLICY

client = TestClient(app)

FINANCIAL_DISCLAIMER_SNIPPET = "não é aconselhamento financeiro definitivo"


@pytest.fixture
def registry_spy(monkeypatch):
    """Registra todo acesso ao provider registry feito pelo pipeline."""
    calls: list[tuple[str, str | None]] = []
    original_get = provider_registry.get
    original_mock = provider_registry.mock

    def spy_get(name):
        calls.append(("get", name))
        return original_get(name)

    def spy_mock():
        calls.append(("mock", None))
        return original_mock()

    monkeypatch.setattr(provider_registry, "get", spy_get)
    monkeypatch.setattr(provider_registry, "mock", spy_mock)
    return calls


def test_dangerous_task_type_blocked_without_provider_call(registry_spy):
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Execute isto",
            "provider": "gemini",
            "task_type": "execute_command",
            "allow_real_provider": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "blocked"
    assert data["error_code"] == "PROJECT_POLICY_BLOCKED"
    assert data["provider_used"] == "none"
    # Nenhum provider (nem mock) foi tocado: policy roda antes de tudo.
    assert registry_spy == []


def test_dangerous_payload_key_blocked_without_provider_call(registry_spy):
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise",
            "provider": "mock",
            "metadata": {"command": "rm -rf /"},
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "blocked"
    assert data["error_code"] == "PROJECT_POLICY_BLOCKED"
    assert data["provider_used"] == "none"
    assert registry_spy == []


def test_dangerous_task_blocked_even_with_enforcement_flag_off(
    monkeypatch, registry_spy
):
    # O bloqueio estrutural (execução/escrita/deleção) não depende da flag.
    monkeypatch.setenv(FLAG_ENFORCE_PROJECT_POLICY, "false")

    response = client.post(
        "/api/orchestrate",
        json={"message": "Delete tudo", "provider": "mock", "task_type": "delete_files"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "blocked"
    assert registry_spy == []


def test_missing_message_fails_controlled(registry_spy):
    response = client.post("/api/orchestrate", json={"provider": "mock"})

    assert response.status_code == 422
    assert "detail" in response.json()
    assert "Traceback" not in response.text
    assert registry_spy == []


def test_empty_message_fails_controlled(registry_spy):
    response = client.post(
        "/api/orchestrate", json={"message": "", "provider": "mock"}
    )

    assert response.status_code == 422
    assert registry_spy == []


def test_policy_block_returns_standardized_error_contract():
    response = client.post(
        "/api/orchestrate",
        json={"message": "Execute", "provider": "mock", "task_type": "exec_shell"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "blocked"
    assert data["error_code"] == "PROJECT_POLICY_BLOCKED"
    assert data["blocked_reason"]
    assert data["warning_codes"]
    assert "bloqueada por policy" in data["answer"]
    assert data["model"] == "none"


def test_malicious_payload_does_not_leak_stack_trace():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "'; DROP TABLE users; --",
            "provider": "mock",
            "task_type": "drop_database",
            "context": {"shell": "powershell -c evil"},
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert "Traceback" not in response.text
    assert "most recent call last" not in response.text


def test_finance_advice_disclaimer_is_mandatory():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Devo investir tudo em uma ação?",
            "provider": "mock",
            "task_type": "finance_advice",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert FINANCIAL_DISCLAIMER_SNIPPET in data["answer"]
    assert "validação humana" in data["answer"]
    assert "FINANCIAL_DISCLAIMER" in data["warning_codes"]


def test_finance_advice_disclaimer_survives_provider_fallback():
    # Mesmo com provider real bloqueado + fallback, o disclaimer permanece.
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Devo investir tudo?",
            "provider": "gemini",
            "task_type": "finance_advice",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["safe_mode_blocked"] is True
    assert data["provider_used"] == "mock"
    assert FINANCIAL_DISCLAIMER_SNIPPET in data["answer"]


def test_context_from_memory_without_persistence_stays_off(monkeypatch):
    monkeypatch.delenv("PEDROCORE_REPORT_MEMORY_PERSISTENCE", raising=False)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Status?",
            "provider": "mock",
            "task_type": "project_status",
            "context_from_memory": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["memory_used"] is False
    assert "REPORT_MEMORY_DISABLED" in data["warning_codes"]
