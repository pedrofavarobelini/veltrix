"""Autorização e provenance das rotas V1 de Report Memory (Etapa 0A).

Todos os callers e segredos são sintéticos. Os testes usam somente TestClient,
memória in-process e provider mock; nenhuma chamada externa é possível.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.schemas import SHARED_OR_UNKNOWN_PROJECT_ID
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
)
from app.modules.contracts import codes
from app.modules.observability.service import FLAG_ENABLED, observability_service
from app.modules.report_memory.service import FLAG_PERSISTENCE, report_memory_service

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
ALPHA_KEY = "alpha-tool-credential-synthetic"
BETA_KEY = "beta-tool-credential-synthetic"
LEGACY_KEY = "legacy-shared-credential-synthetic"


def _entry(project_id: str, key: str, *, role: str = "technical_tool") -> dict:
    return {
        "credential_id": f"{project_id}-{role}",
        "api_key": key,
        "project_id": project_id,
        "role": role,
        "environment": "development",
        "allowed_origins": [project_id],
    }


def _configure_registry(monkeypatch, *entries: dict) -> None:
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, json.dumps(list(entries)))
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)


def _report(project_id: str) -> dict:
    return {
        "project_id": project_id,
        "report_type": "qa_run",
        "status": "passed",
        "summary": "Relatório sintético de autorização.",
    }


def _headers(key: str) -> dict[str, str]:
    return {AUTH_HEADER: key}


@pytest.fixture(autouse=True)
def clean_authorization_state(monkeypatch):
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.delenv(FLAG_ENABLED, raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    report_memory_service.reset()
    observability_service.reset()
    yield
    report_memory_service.reset()
    observability_service.reset()


def test_registered_project_and_producer_are_authorized(monkeypatch):
    """Caso A: projeto, producer, role e environment vêm da identidade."""
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))
    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.setenv("APP_ENV", "development")

    response = client.post(
        "/api/reports/analyze",
        json=_report("alpha"),
        headers=_headers(ALPHA_KEY),
    )

    assert response.status_code == 200
    assert response.json()["report"]["project_id"] == "alpha"
    executions = observability_service.list(task="qa_report_analysis")
    assert len(executions) == 1
    record = observability_service.get(executions[0].execution_id)
    assert record is not None
    assert record.caller == {
        "producer": "alpha-technical_tool",
        "credential_id": "alpha-technical_tool",
        "authenticated": True,
        "identity_strength": "registered",
        "project_id_authenticated": "alpha",
        "project_id_authorized": "alpha",
        "caller_role": "technical_tool",
        "environment": "development",
    }


def test_registered_project_spoofing_is_rejected(monkeypatch):
    """Caso B: identidade A + payload B nunca produz 200."""
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))

    response = client.post(
        "/api/reports/ingest",
        json=_report("beta"),
        headers=_headers(ALPHA_KEY),
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == codes.CALLER_ORIGIN_MISMATCH
    assert report_memory_service.snapshot("beta") is None


def test_registered_caller_cannot_read_or_write_another_project(monkeypatch):
    """Caso C: isolamento vale para ingest e summary."""
    _configure_registry(
        monkeypatch,
        _entry("alpha", ALPHA_KEY),
        _entry("beta", BETA_KEY),
    )
    accepted = client.post(
        "/api/reports/ingest",
        json=_report("alpha"),
        headers=_headers(ALPHA_KEY),
    )
    assert accepted.status_code == 200
    assert accepted.json()["stored"] is True

    write = client.post(
        "/api/reports/ingest",
        json=_report("alpha"),
        headers=_headers(BETA_KEY),
    )
    read = client.get(
        "/api/project-memory/alpha/summary",
        headers=_headers(BETA_KEY),
    )

    assert write.status_code == 403
    assert read.status_code == 403
    assert write.json()["error_code"] == codes.CALLER_ORIGIN_MISMATCH
    assert read.json()["error_code"] == codes.CALLER_ORIGIN_MISMATCH
    snapshot = report_memory_service.snapshot("alpha")
    assert snapshot is not None
    assert snapshot.source_count == 1


def test_registry_requires_identity(monkeypatch):
    """Caso D: registry ativo + credencial ausente falha fechado."""
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))

    response = client.post("/api/reports/analyze", json=_report("alpha"))

    assert response.status_code == 401
    assert response.json()["error_code"] == codes.CALLER_CREDENTIAL_MISSING


def test_invalid_registered_credential_is_rejected(monkeypatch):
    """Caso E: credencial desconhecida falha fechado."""
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))

    response = client.post(
        "/api/reports/analyze",
        json=_report("alpha"),
        headers=_headers("invalid-synthetic-credential"),
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == codes.CALLER_CREDENTIAL_UNKNOWN


def test_legacy_shared_credential_keeps_restricted_namespace(monkeypatch):
    """Caso F: LEGACY válido continua funcional sem assumir projeto real."""
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, LEGACY_KEY)

    response = client.post(
        "/api/reports/ingest",
        json=_report(SHARED_OR_UNKNOWN_PROJECT_ID),
        headers=_headers(LEGACY_KEY),
    )

    assert response.status_code == 200
    assert response.json()["stored"] is True
    warning_codes = [item["code"] for item in response.json()["warnings"]]
    assert codes.CALLER_IDENTITY_SHARED_CREDENTIAL in warning_codes


def test_legacy_shared_credential_cannot_claim_concrete_project(monkeypatch):
    """Caso G: LEGACY + projeto concreto é bypass e deve ser rejeitado."""
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, LEGACY_KEY)

    response = client.post(
        "/api/reports/analyze",
        json=_report("alpha"),
        headers=_headers(LEGACY_KEY),
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == codes.CALLER_IDENTITY_AMBIGUOUS


def test_invalid_legacy_credential_preserves_http_contract(monkeypatch):
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, LEGACY_KEY)

    response = client.post(
        "/api/reports/analyze",
        json=_report(SHARED_OR_UNKNOWN_PROJECT_ID),
        headers=_headers("wrong-legacy-credential"),
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == codes.INTERNAL_AUTH_INVALID


def test_common_consumer_has_no_report_memory_capability(monkeypatch):
    _configure_registry(
        monkeypatch,
        _entry("alpha", ALPHA_KEY, role="common_consumer"),
    )

    response = client.post(
        "/api/reports/analyze",
        json=_report("alpha"),
        headers=_headers(ALPHA_KEY),
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == codes.CALLER_REPORT_ACCESS_NOT_ALLOWED


def test_unregistered_production_request_is_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    response = client.post("/api/reports/analyze", json=_report("pedrocore"))

    assert response.status_code == 401
    assert response.json()["error_code"] == codes.CALLER_CREDENTIAL_MISSING


def test_orchestration_caller_identity_does_not_regress(monkeypatch):
    """Caso H: a integração existente de orchestration permanece funcional."""
    _configure_registry(monkeypatch, _entry("pedrocore", ALPHA_KEY))

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Verificação local de regressão.",
            "provider": "mock",
            "task_type": "general_chat",
            "origin_system": "pedrocore",
        },
        headers=_headers(ALPHA_KEY),
    )

    assert response.status_code == 200
    assert response.json()["project_id"] == "pedrocore"
    assert response.json()["provider_used"] == "mock"
