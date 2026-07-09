import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.report_intelligence.schemas import TechnicalReportInput
from app.modules.report_memory.service import (
    FLAG_MEMORY_DIR,
    FLAG_PERSISTENCE,
    report_memory_service,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_memory(monkeypatch):
    monkeypatch.delenv(FLAG_PERSISTENCE, raising=False)
    monkeypatch.delenv(FLAG_MEMORY_DIR, raising=False)
    report_memory_service.reset()
    yield
    report_memory_service.reset()


def _report(**overrides) -> dict:
    base = {
        "project_id": "demo-project",
        "report_type": "qa_run",
        "status": "passed",
        "summary": "Execução concluída com sucesso.",
        "next_steps": ["Rodar suíte full"],
        "created_at": "2026-07-09T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_persistence_off_by_default_and_ingest_stores_nothing():
    response = client.post("/api/reports/ingest", json=_report())
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "disabled"
    assert data["stored"] is False
    assert data["memory_id"] is None
    codes = [w["code"] for w in data["warnings"]]
    assert "REPORT_MEMORY_DISABLED" in codes
    assert "REPORT_MEMORY_IS_NOT_TRAINING" in codes


def test_analyze_never_persists(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")

    response = client.post("/api/reports/analyze", json=_report())
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert any(s["signal_type"] == "qa_passed" for s in data["signals"])
    assert report_memory_service.snapshot("demo-project") is None


def test_ingest_passed_report_creates_memory(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")

    response = client.post("/api/reports/ingest", json=_report())
    data = response.json()

    assert response.status_code == 200
    assert data["stored"] is True
    assert data["memory_id"]
    assert data["snapshot"]["last_known_status"] == "passed"
    assert data["snapshot"]["source_count"] == 1


def test_provider_real_used_report_is_critical(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")

    response = client.post(
        "/api/reports/ingest",
        json=_report(safety_flags=["provider_real_used"]),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["evaluation"]["passed"] is False
    assert data["evaluation"]["risk_level"] == "critical"
    assert data["evaluation"]["requires_human_review"] is True


def test_summary_returns_last_known_status(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")

    client.post("/api/reports/ingest", json=_report(status="failed"))
    client.post("/api/reports/ingest", json=_report(status="passed"))

    response = client.get("/api/project-memory/demo-project/summary")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["snapshot"]["last_known_status"] == "passed"
    assert data["snapshot"]["source_count"] == 2
    assert "Rodar suíte full" in data["snapshot"]["next_recommended_steps"]


def test_memory_is_isolated_by_project(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")

    client.post("/api/reports/ingest", json=_report(project_id="projeto-a"))

    response = client.get("/api/project-memory/projeto-b/summary")
    data = response.json()

    assert response.status_code == 200
    assert data["snapshot"] is None
    codes = [w["code"] for w in data["warnings"]]
    assert "REPORT_MEMORY_EMPTY" in codes


def test_summary_disabled_when_persistence_off():
    response = client.get("/api/project-memory/demo-project/summary")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "disabled"
    assert data["snapshot"] is None


def test_secrets_are_redacted_before_storage(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")

    client.post(
        "/api/reports/ingest",
        json=_report(
            summary="Deploy ok. api_key=sk-super-secreta-12345",
            next_steps=["Rotacionar token=abc123"],
        ),
    )

    entries = report_memory_service._repository().list("demo-project")
    assert len(entries) == 1
    assert "sk-super-secreta-12345" not in (entries[0].summary or "")
    assert "[REDACTED]" in (entries[0].summary or "")
    assert all("abc123" not in step for step in entries[0].next_steps)


def test_local_json_persistence_uses_configured_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "local_json")
    monkeypatch.setenv(FLAG_MEMORY_DIR, str(tmp_path))

    response = client.post("/api/reports/ingest", json=_report())
    assert response.json()["stored"] is True

    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    stored = json.loads(files[0].read_text(encoding="utf-8"))
    assert stored[0]["project_id"] == "demo-project"
    assert ".env" not in files[0].name


def test_local_json_without_dir_does_not_store(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "local_json")

    response = client.post("/api/reports/ingest", json=_report())
    data = response.json()

    assert data["stored"] is False
    codes = [w["code"] for w in data["warnings"]]
    assert "REPORT_MEMORY_DISABLED" in codes


def test_orchestrate_context_from_memory_false_never_uses_memory(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    client.post("/api/reports/ingest", json=_report(project_id="pedrocore"))

    response = client.post(
        "/api/orchestrate",
        json={"message": "Status?", "provider": "mock", "task_type": "project_status"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["memory_used"] is False
    assert "REPORT_MEMORY_USED" not in data["warning_codes"]


def test_orchestrate_context_from_memory_true_uses_limited_snapshot(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    client.post("/api/reports/ingest", json=_report(project_id="pedrocore"))

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
    assert data["memory_used"] is True
    assert "REPORT_MEMORY_USED" in data["warning_codes"]


def test_orchestrate_memory_request_with_persistence_off_warns():
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


def test_ingest_rejects_invalid_payload():
    response = client.post(
        "/api/reports/ingest", json={"project_id": "x", "report_type": "qa_run"}
    )

    assert response.status_code == 422
