"""Gate 3 — Interaction → Outcome → Persistence → Query."""

import json
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.contracts import codes
from app.modules.interaction_outcomes.repository import (
    InMemoryInteractionOutcomeRepository,
    LocalJsonInteractionOutcomeRepository,
    PostgreSQLInteractionOutcomeRepository,
)
from app.modules.interaction_outcomes.schemas import (
    InteractionOutcome,
    InteractionOutcomeInput,
)
from app.modules.interaction_outcomes.service import interaction_outcome_service
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
ALPHA_KEY = "alpha-outcome-credential-synthetic"
BETA_KEY = "beta-outcome-credential-synthetic"
SIGNATURE_A = "sha256:" + "a" * 64
SIGNATURE_B = "sha256:" + "b" * 64


def _registry(*, alpha_role: str = "technical_tool") -> str:
    return json.dumps(
        [
            {
                "credential_id": "alpha-technical-tool",
                "api_key": ALPHA_KEY,
                "project_id": "alpha",
                "role": alpha_role,
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


def _payload(
    outcome_id: str = "outcome-alpha-1",
    *,
    project_id: str = "alpha",
    producer: str = "alpha-technical-tool",
    conversation_id: str = "conversation-1",
    message_id: str = "message-1",
    feedback: str = "positive",
) -> dict:
    return {
        "schema_version": "1.0",
        "outcome_id": outcome_id,
        "producer": producer,
        "project_id": project_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "task_type": "qa_report_analysis",
        "input_signature": SIGNATURE_A,
        "context_signature": SIGNATURE_B,
        "provider": "mock",
        "model": "mock-v1",
        "response_strategy": "structured_qa",
        "response_characteristics": {
            "length_bucket": "medium",
            "structured": True,
            "contains_citations": False,
            "safety_disclaimer": True,
            "truncated": False,
        },
        "fallback_used": False,
        "regeneration_used": False,
        "feedback": feedback,
        "accepted": True,
        "rejected": False,
        "quality_signals": ["qa_passed", "useful"],
        "audit_id": "audit-synthetic-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _outcome(
    outcome_id: str,
    *,
    project_id: str = "alpha",
    retention_until: datetime | None = None,
) -> InteractionOutcome:
    payload = InteractionOutcomeInput.model_validate(_payload(outcome_id, project_id=project_id))
    now = datetime.now(timezone.utc)
    return InteractionOutcome(
        **payload.model_dump(),
        caller_role="technical_tool",
        environment="development",
        stored_at=now,
        retention_until=retention_until or now + timedelta(days=90),
    )


@pytest.fixture
def postgres_url() -> Iterator[str]:
    value = (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    if not value:
        pytest.skip("PEDROCORE_TEST_POSTGRES_URL não configurada")
    apply_postgresql_migrations(value, MIGRATIONS)
    outcomes = PostgreSQLInteractionOutcomeRepository(value)
    reports = PostgreSQLReportMemoryRepository(value)
    outcomes.clear()
    reports.clear()
    yield value
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
    interaction_outcome_service.reset()
    report_memory_service.reset()
    yield
    interaction_outcome_service.reset()
    report_memory_service.reset()


def test_schema_rejects_raw_content_mass_assignment_and_inconsistent_acceptance(
    monkeypatch,
):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    raw_content = _payload()
    raw_content["input_text"] = "conteúdo que não deve ser armazenado"
    forged_provenance = _payload()
    forged_provenance["caller_role"] = "admin"
    future_version = _payload()
    future_version["schema_version"] = "2.0"
    invalid_signature = _payload()
    invalid_signature["input_signature"] = "sha256:not-a-valid-signature"
    inconsistent = _payload()
    inconsistent["rejected"] = True

    assert (
        client.post(
            "/api/interaction-outcomes",
            headers={AUTH_HEADER: ALPHA_KEY},
            json=raw_content,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/interaction-outcomes",
            headers={AUTH_HEADER: ALPHA_KEY},
            json=forged_provenance,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/interaction-outcomes",
            headers={AUTH_HEADER: ALPHA_KEY},
            json=future_version,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/interaction-outcomes",
            headers={AUTH_HEADER: ALPHA_KEY},
            json=invalid_signature,
        ).status_code
        == 422
    )
    with pytest.raises(ValidationError, match="accepted e rejected"):
        InteractionOutcomeInput.model_validate(inconsistent)


@pytest.mark.parametrize("feedback", ["positive", "negative", "neutral", "unknown"])
def test_feedback_values_are_observational(monkeypatch, feedback):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())

    response = client.post(
        "/api/interaction-outcomes",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_payload(f"outcome-{feedback}", feedback=feedback),
    )

    assert response.status_code == 200
    assert response.json()["outcome"]["feedback"] == feedback
    assert codes.INTERACTION_FEEDBACK_OBSERVATIONAL in {
        item["code"] for item in response.json()["warnings"]
    }


def test_memory_and_local_json_repositories_reconnect_query_and_retain(tmp_path):
    memory = InMemoryInteractionOutcomeRepository()
    assert memory.add(_outcome("memory-one")) is True
    assert memory.add(_outcome("memory-one")) is False
    assert memory.count("alpha", conversation_id="conversation-1") == 1

    local = LocalJsonInteractionOutcomeRepository(tmp_path)
    now = datetime.now(timezone.utc)
    assert local.add(_outcome("expired", retention_until=now - timedelta(minutes=1)))
    assert local.add(_outcome("active", retention_until=now + timedelta(days=1)))
    reconnected = LocalJsonInteractionOutcomeRepository(tmp_path)
    assert reconnected.delete_expired(now) == 1
    assert reconnected.get("alpha", "expired") is None
    assert reconnected.get("alpha", "active") is not None
    assert reconnected.delete_project("alpha") == 1
    assert list(tmp_path.glob("*.json")) == []


def test_postgresql_api_persists_reconnects_queries_and_does_not_train(postgres_url, monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, postgres_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())

    stored = client.post(
        "/api/interaction-outcomes",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_payload(),
    )
    interaction_outcome_service.reset()
    queried = client.get(
        "/api/interaction-outcomes/alpha?conversation_id=conversation-1&message_id=message-1",
        headers={AUTH_HEADER: ALPHA_KEY},
    )
    duplicate = client.post(
        "/api/interaction-outcomes",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_payload(),
    )

    assert stored.status_code == 200
    assert stored.json()["stored"] is True
    assert stored.json()["outcome"]["producer"] == "alpha-technical-tool"
    assert stored.json()["outcome"]["caller_role"] == "technical_tool"
    assert queried.status_code == 200
    assert queried.json()["total"] == 1
    assert queried.json()["items"][0]["outcome_id"] == "outcome-alpha-1"
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["stored"] is False
    assert PostgreSQLReportMemoryRepository(postgres_url).count("alpha") == 0


def test_postgresql_correlation_isolation_retention_and_deletion(postgres_url):
    repository = PostgreSQLInteractionOutcomeRepository(postgres_url)
    now = datetime.now(timezone.utc)
    assert repository.add(_outcome("alpha-one"))
    second = _outcome("alpha-two")
    second = second.model_copy(update={"conversation_id": "conversation-2"})
    assert repository.add(second)
    assert repository.add(_outcome("shared-id", project_id="alpha"))
    assert repository.add(_outcome("shared-id", project_id="beta"))
    assert repository.add(_outcome("expired", retention_until=now - timedelta(minutes=1)))

    assert repository.count("alpha") == 4
    assert repository.count("alpha", conversation_id="conversation-2") == 1
    assert repository.delete_expired(now) == 1
    assert repository.delete_project("alpha") == 3
    assert repository.count("alpha") == 0
    assert repository.count("beta") == 1


def test_outcome_authorization_provenance_idor_and_role_are_fail_closed(postgres_url, monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, postgres_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    accepted = client.post(
        "/api/interaction-outcomes",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_payload(),
    )
    spoofed = _payload("spoofed", producer="beta-technical-tool")
    producer_spoof = client.post(
        "/api/interaction-outcomes",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=spoofed,
    )
    cross_read = client.get(
        "/api/interaction-outcomes/alpha",
        headers={AUTH_HEADER: BETA_KEY},
    )
    cross_delete = client.delete(
        "/api/interaction-outcomes/alpha",
        headers={AUTH_HEADER: BETA_KEY},
    )

    assert accepted.status_code == 200
    assert producer_spoof.status_code == 403
    assert producer_spoof.json()["error_code"] == codes.CALLER_REPORT_PRODUCER_MISMATCH
    assert cross_read.status_code == 403
    assert cross_delete.status_code == 403
    assert PostgreSQLInteractionOutcomeRepository(postgres_url).count("alpha") == 1

    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry(alpha_role="common_consumer"))
    common_consumer = client.post(
        "/api/interaction-outcomes",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_payload("role-blocked"),
    )
    assert common_consumer.status_code == 403
    assert common_consumer.json()["error_code"] == codes.CALLER_REPORT_ACCESS_NOT_ALLOWED


@pytest.mark.parametrize(
    "database_url",
    ["", "postgresql://invalid:invalid@127.0.0.1:1/none?connect_timeout=1"],
)
def test_postgresql_failure_never_falls_back(monkeypatch, database_url):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, database_url)
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())

    response = client.post(
        "/api/interaction-outcomes",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_payload("no-fallback"),
    )

    assert response.status_code == 503
    assert response.json()["error_code"] == (codes.INTERACTION_OUTCOME_PERSISTENCE_UNAVAILABLE)
    assert interaction_outcome_service._memory_repository.count("alpha") == 0
