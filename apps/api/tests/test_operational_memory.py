"""Gate 4 — evidence → candidate → policy → Operational Memory."""

import json
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.contracts import codes
from app.modules.interaction_outcomes.repository import (
    PostgreSQLInteractionOutcomeRepository,
)
from app.modules.interaction_outcomes.service import interaction_outcome_service
from app.modules.operational_memory.policy import OPERATIONAL_MEMORY_POLICY_VERSION
from app.modules.operational_memory.repository import (
    PostgreSQLOperationalMemoryRepository,
)
from app.modules.operational_memory.schemas import (
    LearningCandidateInput,
    PatternType,
)
from app.modules.operational_memory.service import operational_memory_service
from app.modules.report_memory.repository import (
    PostgreSQLReportMemoryRepository,
    apply_postgresql_migrations,
)
from app.modules.report_memory.service import (
    FLAG_DATABASE_URL,
    FLAG_MEMORY_DIR,
    FLAG_PERSISTENCE,
    FLAG_RETENTION_DAYS,
    report_memory_service,
)

client = TestClient(app)
MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
AUTH_HEADER = "X-PedroCore-Api-Key"
ALPHA_KEY = "alpha-memory-credential-synthetic"
BETA_KEY = "beta-memory-credential-synthetic"
SIGNATURE_A = "sha256:" + "a" * 64
SIGNATURE_B = "sha256:" + "b" * 64


def _registry() -> str:
    return json.dumps(
        [
            {
                "credential_id": "alpha-technical-tool",
                "api_key": ALPHA_KEY,
                "project_id": "alpha",
                "role": "technical_tool",
                "environment": "development",
                "allowed_origins": ["alpha"],
            },
            {
                "credential_id": "beta-technical-tool",
                "api_key": BETA_KEY,
                "project_id": "beta",
                "role": "technical_tool",
                "environment": "development",
                "allowed_origins": ["beta"],
            },
        ]
    )


def _outcome_payload(
    outcome_id: str,
    *,
    project_id: str = "alpha",
    producer: str = "alpha-technical-tool",
    task_type: str = "qa_report_analysis",
) -> dict:
    return {
        "schema_version": "1.0",
        "outcome_id": outcome_id,
        "producer": producer,
        "project_id": project_id,
        "conversation_id": f"conversation-{outcome_id}",
        "message_id": f"message-{outcome_id}",
        "task_type": task_type,
        "input_signature": SIGNATURE_A,
        "context_signature": SIGNATURE_B,
        "provider": "mock",
        "model": "mock-v1",
        "response_strategy": "structured_qa",
        "feedback": "positive",
        "accepted": True,
        "rejected": False,
        "quality_signals": ["useful"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _report_payload(report_id: str, status: str) -> dict:
    return {
        "schema_version": "2.0",
        "report_id": report_id,
        "report_type": "qa_evidence",
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "status": status,
            "summary": f"QA sintético {status}",
            "test_scope": "operational-memory-fixture",
            "passed": 1 if status == "passed" else 0,
            "failed": 1 if status == "failed" else 0,
        },
    }


def _candidate_payload(
    candidate_id: str,
    source_id: str,
    *,
    source_type: str = "interaction_outcome",
    effect: str = "supports",
    pattern_type: str = "SUCCESS_PATTERN",
    pattern_key: str = "qa.structured.success",
) -> dict:
    return {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "pattern_type": pattern_type,
        "pattern_key": pattern_key,
        "task_type": "qa_report_analysis",
        "summary": "Respostas estruturadas têm resultado consistente.",
        "evidence": [
            {
                "source_type": source_type,
                "source_id": source_id,
                "effect": effect,
            }
        ],
    }


def _post_outcome(outcome_id: str) -> None:
    response = client.post(
        "/api/interaction-outcomes",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_outcome_payload(outcome_id),
    )
    assert response.status_code == 200
    assert response.json()["stored"] is True


def _post_report(report_id: str, status: str) -> None:
    response = client.post(
        "/api/reports/v2/ingest",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_report_payload(report_id, status),
    )
    assert response.status_code == 200
    assert response.json()["stored"] is True


@pytest.fixture
def postgres_url() -> Iterator[str]:
    value = (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    if not value:
        pytest.skip("PEDROCORE_TEST_POSTGRES_URL não configurada")
    apply_postgresql_migrations(value, MIGRATIONS)
    operational = PostgreSQLOperationalMemoryRepository(value)
    outcomes = PostgreSQLInteractionOutcomeRepository(value)
    reports = PostgreSQLReportMemoryRepository(value)
    operational.clear()
    outcomes.clear()
    reports.clear()
    yield value
    operational.clear()
    outcomes.clear()
    reports.clear()


@pytest.fixture(autouse=True)
def clean_services(monkeypatch):
    for name in (
        FLAG_CALLER_REGISTRY,
        FLAG_DATABASE_URL,
        FLAG_MEMORY_DIR,
        FLAG_PERSISTENCE,
        FLAG_RETENTION_DAYS,
    ):
        monkeypatch.delenv(name, raising=False)
    operational_memory_service.reset()
    interaction_outcome_service.reset()
    report_memory_service.reset()
    yield
    operational_memory_service.reset()
    interaction_outcome_service.reset()
    report_memory_service.reset()


@pytest.mark.parametrize("pattern_type", list(PatternType))
def test_all_pattern_types_are_strictly_modeled(pattern_type):
    candidate = LearningCandidateInput.model_validate(
        _candidate_payload(
            f"candidate-{pattern_type.value.lower()}",
            "evidence-1",
            pattern_type=pattern_type.value,
            pattern_key=f"pattern.{pattern_type.value.lower()}",
        )
    )
    assert candidate.pattern_type is pattern_type


def test_candidate_schema_rejects_future_version_and_derived_confidence(
    monkeypatch,
):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    future = _candidate_payload("candidate-future", "missing")
    future["schema_version"] = "2.0"
    forged = _candidate_payload("candidate-forged", "missing")
    forged["confidence"] = 1.0

    assert (
        client.post(
            "/api/operational-memory/candidates",
            headers={AUTH_HEADER: ALPHA_KEY},
            json=future,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/operational-memory/candidates",
            headers={AUTH_HEADER: ALPHA_KEY},
            json=forged,
        ).status_code
        == 422
    )


def test_one_event_is_detected_three_distinct_events_promote_and_duplicate_is_safe(
    monkeypatch,
):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    responses = []
    for index in range(1, 4):
        outcome_id = f"success-{index}"
        _post_outcome(outcome_id)
        responses.append(
            client.post(
                "/api/operational-memory/candidates",
                headers={AUTH_HEADER: ALPHA_KEY},
                json=_candidate_payload(f"candidate-{index}", outcome_id),
            )
        )

    assert responses[0].status_code == 200
    assert responses[0].json()["memory"]["lifecycle"] == "DETECTED"
    assert codes.OPERATIONAL_SINGLE_EVIDENCE_NOT_PROMOTED in {
        item["code"] for item in responses[0].json()["warnings"]
    }
    assert responses[1].json()["memory"]["lifecycle"] == "DETECTED"
    assert responses[2].json()["memory"]["lifecycle"] == "ACTIVE"
    assert responses[2].json()["memory"]["sample_size"] == 3
    assert responses[2].json()["memory"]["policy_version"] == (OPERATIONAL_MEMORY_POLICY_VERSION)
    assert responses[2].json()["memory"]["confidence"] >= 0.70

    duplicate = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_candidate_payload("candidate-3", "success-3"),
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["stored"] is False
    assert duplicate.json()["memory"]["sample_size"] == 3


def test_candidate_and_pattern_summaries_are_redacted(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    _post_outcome("redaction-evidence")
    payload = _candidate_payload("redaction-candidate", "redaction-evidence")
    payload["summary"] = "Padrão observado com token=synthetic-secret-value"

    response = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=payload,
    )

    assert response.status_code == 200
    assert "synthetic-secret-value" not in response.text
    assert "[REDACTED]" in response.json()["candidate"]["summary"]
    assert "[REDACTED]" in response.json()["memory"]["pattern"]["summary"]


def test_contradiction_is_preserved_and_reduces_confidence(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    active_confidence = 0.0
    for index in range(1, 4):
        outcome_id = f"support-{index}"
        _post_outcome(outcome_id)
        response = client.post(
            "/api/operational-memory/candidates",
            headers={AUTH_HEADER: ALPHA_KEY},
            json=_candidate_payload(f"support-candidate-{index}", outcome_id),
        )
        active_confidence = response.json()["memory"]["confidence"]
    _post_outcome("contradiction-1")
    contradicted = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_candidate_payload(
            "contradiction-candidate",
            "contradiction-1",
            effect="contradicts",
        ),
    )

    memory = contradicted.json()["memory"]
    assert contradicted.status_code == 200
    assert len(memory["evidence"]) == 3
    assert len(memory["contradictions"]) == 1
    assert memory["confidence"] < active_confidence
    assert memory["confidence_breakdown"]["contradiction_penalty"] > 0
    assert codes.OPERATIONAL_CONTRADICTION_PRESERVED in {
        item["code"] for item in contradicted.json()["warnings"]
    }


def test_validated_later_qa_evidence_resolves_risk_without_erasing_history(
    monkeypatch,
):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    active = None
    for index in range(1, 4):
        report_id = f"failed-qa-{index}"
        _post_report(report_id, "failed")
        active = client.post(
            "/api/operational-memory/candidates",
            headers={AUTH_HEADER: ALPHA_KEY},
            json=_candidate_payload(
                f"risk-candidate-{index}",
                report_id,
                source_type="report",
                pattern_type="RISK_PATTERN",
                pattern_key="qa.recurring.failure",
            ),
        )
    assert active is not None
    assert active.json()["memory"]["lifecycle"] == "ACTIVE"

    _post_report("qa-resolution", "passed")
    resolved = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_candidate_payload(
            "risk-resolution",
            "qa-resolution",
            source_type="report",
            effect="resolves",
            pattern_type="RISK_PATTERN",
            pattern_key="qa.recurring.failure",
        ),
    )

    memory = resolved.json()["memory"]
    assert resolved.status_code == 200
    assert memory["lifecycle"] == "RESOLVED"
    assert memory["sample_size"] == 4
    assert len(memory["evidence"]) == 4
    assert any(
        transition["to_lifecycle"] == "RESOLVED" for transition in memory["lifecycle_history"]
    )
    assert codes.OPERATIONAL_PATTERN_RESOLVED in {
        item["code"] for item in resolved.json()["warnings"]
    }


def test_missing_cross_project_or_unavailable_human_evidence_is_rejected(
    monkeypatch,
):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    missing = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_candidate_payload("candidate-missing", "not-in-alpha"),
    )
    human = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_candidate_payload(
            "candidate-human",
            "human-review-1",
            source_type="human_validation",
        ),
    )

    assert missing.status_code == 422
    assert missing.json()["error_code"] == codes.OPERATIONAL_EVIDENCE_NOT_FOUND
    assert human.status_code == 422
    assert human.json()["error_code"] == codes.OPERATIONAL_EVIDENCE_NOT_FOUND


def test_local_json_reconnects_without_automatic_behavior_change(tmp_path, monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "local_json")
    monkeypatch.setenv(FLAG_MEMORY_DIR, str(tmp_path))
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    _post_outcome("local-evidence")
    stored = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_candidate_payload("local-candidate", "local-evidence"),
    )
    operational_memory_service.reset()
    queried = client.get(
        "/api/operational-memory/alpha",
        headers={AUTH_HEADER: ALPHA_KEY},
    )

    assert stored.status_code == 200
    assert stored.json()["memory"]["lifecycle"] == "DETECTED"
    assert queried.status_code == 200
    assert queried.json()["total"] == 1
    assert queried.json()["items"][0]["sample_size"] == 1
    assert report_memory_service._memory_repo.count("alpha") == 0


def test_postgresql_reconnect_query_isolation_and_deletion(postgres_url, monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, postgres_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    _post_outcome("postgres-evidence")
    stored = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_candidate_payload("postgres-candidate", "postgres-evidence"),
    )
    operational_memory_service.reset()
    queried = client.get(
        "/api/operational-memory/alpha?lifecycle=DETECTED&pattern_type=SUCCESS_PATTERN",
        headers={AUTH_HEADER: ALPHA_KEY},
    )
    cross_project = client.get(
        "/api/operational-memory/alpha",
        headers={AUTH_HEADER: BETA_KEY},
    )
    deleted = client.delete(
        "/api/operational-memory/alpha",
        headers={AUTH_HEADER: ALPHA_KEY},
    )

    assert stored.status_code == 200
    assert queried.status_code == 200
    assert queried.json()["total"] == 1
    assert cross_project.status_code == 403
    assert deleted.status_code == 200
    assert deleted.json()["deleted_candidates"] == 1
    assert deleted.json()["deleted_memories"] == 1


def test_postgresql_retention_deletes_expired_candidate_and_memory(postgres_url, monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, postgres_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    _post_outcome("retention-evidence")
    stored = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_candidate_payload("retention-candidate", "retention-evidence"),
    ).json()
    service_repository = operational_memory_service._repository()
    assert service_repository is not None
    candidate = service_repository.get_candidate("alpha", "retention-candidate")
    memory = service_repository.get_memory_by_pattern("alpha", stored["candidate"]["pattern_id"])
    assert candidate is not None
    assert memory is not None
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired_candidate = candidate.model_copy(
        update={"candidate_id": "expired-candidate", "retention_until": past}
    )
    expired_memory = memory.model_copy(update={"retention_until": past})
    repository = PostgreSQLOperationalMemoryRepository(postgres_url)
    assert repository.save_evaluation(expired_candidate, expired_memory)

    deleted_candidates, deleted_memories = repository.delete_expired(datetime.now(timezone.utc))
    assert deleted_candidates == 1
    assert deleted_memories == 1


@pytest.mark.parametrize(
    "database_url",
    ["", "postgresql://invalid:invalid@127.0.0.1:1/none?connect_timeout=1"],
)
def test_postgresql_failure_never_falls_back(monkeypatch, database_url):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, database_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    response = client.post(
        "/api/operational-memory/candidates",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_candidate_payload("no-fallback", "unresolved"),
    )

    assert response.status_code == 503
    assert response.json()["error_code"] == (codes.OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE)
    assert operational_memory_service._memory_repository.count_memory("alpha") == 0
