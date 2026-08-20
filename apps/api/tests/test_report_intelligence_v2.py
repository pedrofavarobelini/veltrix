"""Gate 1 — Common Envelope V2, provenance e compatibilidade V1."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.schemas import SHARED_OR_UNKNOWN_PROJECT_ID
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
    FLAG_INTERNAL_CREDENTIAL_ID,
)
from app.modules.contracts import codes
from app.modules.report_memory.service import FLAG_PERSISTENCE, report_memory_service

client = TestClient(app)

AUTH_HEADER = "X-PedroCore-Api-Key"
ALPHA_KEY = "alpha-v2-credential-synthetic"
BETA_KEY = "beta-v2-credential-synthetic"
LEGACY_KEY = "legacy-v2-credential-synthetic"


def _entry(project_id: str, key: str) -> dict:
    return {
        "credential_id": f"{project_id}-technical-tool",
        "api_key": key,
        "project_id": project_id,
        "role": "technical_tool",
        "environment": "development",
        "allowed_origins": [project_id],
    }


def _configure_registry(monkeypatch, *entries: dict) -> None:
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, json.dumps(list(entries)))
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.delenv(FLAG_INTERNAL_CREDENTIAL_ID, raising=False)


def _v2(
    *,
    project_id: str = "alpha",
    producer: str = "alpha-technical-tool",
    report_id: str = "report-v2-001",
    report_type: str = "qa_evidence",
) -> dict:
    return {
        "schema_version": "2.0",
        "report_id": report_id,
        "report_type": report_type,
        "producer": producer,
        "project_id": project_id,
        "run_id": "run-v2-001",
        "conversation_id": "conversation-v2-001",
        "created_at": "2026-08-20T12:00:00+00:00",
        "payload": {
            "status": "passed",
            "summary": "Gate sintético concluído.",
            "findings": ["Finding preservado"],
            "suggested_fixes": ["Fix preservado"],
            "signals": [{"type": "reported", "confidence": 0.8}],
            "evidence": [
                "pytest: passed",
                {"kind": "test", "result": "passed"},
            ],
            "metadata": {"suite": "gate-1"},
        },
    }


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.delenv(FLAG_INTERNAL_CREDENTIAL_ID, raising=False)
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    report_memory_service.reset()
    yield
    report_memory_service.reset()


def test_v1_is_adapted_to_v2_without_losing_payload(monkeypatch):
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))
    response = client.post(
        "/api/reports/ingest",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={
            "report_id": "legacy-report-001",
            "project_id": "alpha",
            "report_type": "qa_run",
            "status": "passed",
            "findings": ["finding-v1"],
            "suggested_fixes": ["fix-v1"],
            "signals": [{"type": "legacy-signal"}],
            "evidence": [{"kind": "legacy", "value": "preserved"}],
            "metadata": {"legacy": True},
        },
    )

    assert response.status_code == 200
    assert response.json()["stored"] is True
    repository = report_memory_service._repository()
    assert repository is not None
    entries = repository.list("alpha")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.schema_version == "2.0"
    assert entry.report_id == "legacy-report-001"
    assert entry.producer == "alpha-technical-tool"
    assert entry.findings == ["finding-v1"]
    assert entry.suggested_fixes == ["fix-v1"]
    assert entry.source_signals == [{"type": "legacy-signal"}]
    assert entry.evidence == [{"kind": "legacy", "value": "preserved"}]
    assert entry.metadata == {"legacy": True}


@pytest.mark.parametrize(
    "report_type",
    ["interaction_quality", "qa_evidence", "risk_analysis", "execution_outcome"],
)
def test_all_initial_v2_report_types_are_accepted(monkeypatch, report_type):
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))
    response = client.post(
        "/api/reports/v2/analyze",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_v2(report_type=report_type, report_id=f"report-{report_type}"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["report"]["schema_version"] == "2.0"
    assert data["report"]["report_type"] == report_type
    assert data["report"]["payload"]["findings"] == ["Finding preservado"]
    assert data["report"]["payload"]["signals"][0]["type"] == "reported"
    assert data["report"]["payload"]["evidence"][1]["kind"] == "test"


def test_unknown_schema_version_is_rejected(monkeypatch):
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))
    payload = _v2()
    payload["schema_version"] = "99.0"

    response = client.post(
        "/api/reports/v2/analyze",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=payload,
    )

    assert response.status_code == 422


def test_unknown_report_type_and_wrong_typed_payload_are_rejected(monkeypatch):
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))
    unknown = _v2(report_type="unknown")
    wrong_payload = _v2(report_type="qa_evidence")
    wrong_payload["payload"]["risk_level"] = "high"

    unknown_response = client.post(
        "/api/reports/v2/analyze",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=unknown,
    )
    wrong_response = client.post(
        "/api/reports/v2/analyze",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=wrong_payload,
    )

    assert unknown_response.status_code == 422
    assert wrong_response.status_code == 422


def test_v2_missing_or_invalid_identity_is_rejected(monkeypatch):
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))

    missing = client.post("/api/reports/v2/analyze", json=_v2())
    invalid = client.post(
        "/api/reports/v2/analyze",
        headers={AUTH_HEADER: "invalid-v2-credential"},
        json=_v2(),
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json()["error_code"] == codes.CALLER_CREDENTIAL_MISSING
    assert invalid.json()["error_code"] == codes.CALLER_CREDENTIAL_UNKNOWN


def test_v2_producer_spoofing_is_rejected(monkeypatch):
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))
    response = client.post(
        "/api/reports/v2/analyze",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_v2(producer="forged-producer"),
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == codes.CALLER_REPORT_PRODUCER_MISMATCH


def test_v2_cross_project_spoofing_is_rejected(monkeypatch):
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))
    response = client.post(
        "/api/reports/v2/ingest",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_v2(project_id="beta"),
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == codes.CALLER_ORIGIN_MISMATCH
    assert report_memory_service.snapshot("beta") is None


def test_v2_duplicate_report_id_has_no_second_effect(monkeypatch):
    _configure_registry(monkeypatch, _entry("alpha", ALPHA_KEY))
    first = client.post(
        "/api/reports/v2/ingest",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_v2(),
    )
    second = client.post(
        "/api/reports/v2/ingest",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_v2(),
    )

    assert first.json()["stored"] is True
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert second.json()["stored"] is False
    assert second.json()["duplicate"] is True
    assert second.json()["memory_id"] == first.json()["memory_id"]
    assert second.json()["snapshot"]["source_count"] == 1
    warning_codes = [item["code"] for item in second.json()["warnings"]]
    assert codes.REPORT_DUPLICATE_IGNORED in warning_codes


def test_report_id_idempotency_is_scoped_by_project(monkeypatch):
    _configure_registry(
        monkeypatch,
        _entry("alpha", ALPHA_KEY),
        _entry("beta", BETA_KEY),
    )
    alpha = client.post(
        "/api/reports/v2/ingest",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_v2(),
    )
    beta = client.post(
        "/api/reports/v2/ingest",
        headers={AUTH_HEADER: BETA_KEY},
        json=_v2(project_id="beta", producer="beta-technical-tool"),
    )

    assert alpha.json()["stored"] is True
    assert beta.json()["stored"] is True
    alpha_snapshot = report_memory_service.snapshot("alpha")
    beta_snapshot = report_memory_service.snapshot("beta")
    assert alpha_snapshot is not None
    assert beta_snapshot is not None
    assert alpha_snapshot.source_count == 1
    assert beta_snapshot.source_count == 1


def test_v2_legacy_is_restricted_but_compatible(monkeypatch):
    monkeypatch.setenv(FLAG_INTERNAL_API_KEY, LEGACY_KEY)
    monkeypatch.setenv(FLAG_INTERNAL_CREDENTIAL_ID, "legacy-v2-tool")
    valid = client.post(
        "/api/reports/v2/analyze",
        headers={AUTH_HEADER: LEGACY_KEY},
        json=_v2(
            project_id=SHARED_OR_UNKNOWN_PROJECT_ID,
            producer="legacy-v2-tool",
        ),
    )
    bypass = client.post(
        "/api/reports/v2/analyze",
        headers={AUTH_HEADER: LEGACY_KEY},
        json=_v2(producer="legacy-v2-tool"),
    )

    assert valid.status_code == 200
    assert codes.CALLER_IDENTITY_SHARED_CREDENTIAL in [
        item["code"] for item in valid.json()["warnings"]
    ]
    assert bypass.status_code == 403
    assert bypass.json()["error_code"] == codes.CALLER_IDENTITY_AMBIGUOUS
