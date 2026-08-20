"""Gate 5 — bounded, explainable retrieval over Operational Memory."""

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
from app.modules.observability.service import FLAG_ENABLED, observability_service
from app.modules.operational_memory.repository import (
    PostgreSQLOperationalMemoryRepository,
)
from app.modules.operational_memory.schemas import (
    CandidateDecision,
    ConfidenceBreakdown,
    EvidenceEffect,
    EvidenceReference,
    EvidenceSourceType,
    LearningCandidate,
    MemoryLifecycle,
    OperationalMemoryEntry,
    OperationalPattern,
    PatternType,
)
from app.modules.operational_memory.service import operational_memory_service
from app.modules.report_memory.repository import apply_postgresql_migrations
from app.modules.report_memory.service import FLAG_DATABASE_URL, FLAG_PERSISTENCE
from app.modules.retrieval.schemas import RetrievalQuery
from app.modules.retrieval.service import retrieval_service

client = TestClient(app)
MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"
AUTH_HEADER = "X-PedroCore-Api-Key"
API_KEY = "retrieval-alpha-key-synthetic"


def _registry() -> str:
    return json.dumps(
        [
            {
                "credential_id": "alpha-technical-tool",
                "api_key": API_KEY,
                "project_id": "alpha",
                "role": "technical_tool",
                "environment": "development",
                "allowed_origins": ["alpha"],
            }
        ]
    )


def _evidence(source_id: str, observed_at: datetime) -> EvidenceReference:
    return EvidenceReference(
        source_type=EvidenceSourceType.INTERACTION_OUTCOME,
        source_id=source_id,
        effect=EvidenceEffect.SUPPORTS,
        source_reliability=0.8,
        evidence_strength=0.8,
        context_match=1.0,
        observed_at=observed_at,
    )


def _memory(
    key: str,
    summary: str,
    *,
    pattern_type: PatternType = PatternType.SUCCESS_PATTERN,
    lifecycle: MemoryLifecycle = MemoryLifecycle.ACTIVE,
    task_type: str = "code_maintenance",
    confidence: float = 0.8,
    updated_at: datetime | None = None,
) -> tuple[LearningCandidate, OperationalMemoryEntry]:
    now = updated_at or datetime.now(timezone.utc)
    pattern_id = f"pat_{key.replace('.', '_')}"
    memory_id = f"mem_{key.replace('.', '_')}"
    evidence = [_evidence(f"ev-{key}", now)]
    candidate = LearningCandidate(
        candidate_id=f"cand-{key}",
        producer="alpha-technical-tool",
        project_id="alpha",
        pattern_type=pattern_type,
        pattern_key=key,
        task_type=task_type,
        summary=summary,
        pattern_id=pattern_id,
        evidence=evidence,
        confidence=confidence,
        decision=CandidateDecision.PROMOTED,
        policy_version="operational-memory-v1",
        caller_role="technical_tool",
        environment="development",
        created_at=now,
        stored_at=now,
        retention_until=now + timedelta(days=3650),
    )
    memory = OperationalMemoryEntry(
        memory_id=memory_id,
        project_id="alpha",
        pattern=OperationalPattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            pattern_key=key,
            task_type=task_type,
            summary=summary,
        ),
        confidence=confidence,
        confidence_breakdown=ConfidenceBreakdown(
            source_reliability=0.8,
            evidence_strength=0.8,
            frequency=1.0,
            recency=1.0,
            context_match=1.0,
            qa_validation=0.0,
            human_validation=0.0,
            contradiction_penalty=0.0,
        ),
        lifecycle=lifecycle,
        candidate_ids=[candidate.candidate_id],
        evidence=evidence,
        sample_size=3,
        policy_version="operational-memory-v1",
        created_at=now,
        updated_at=now,
        retention_until=now + timedelta(days=3650),
    )
    return candidate, memory


def _save(*memories: tuple[LearningCandidate, OperationalMemoryEntry]) -> None:
    repository = operational_memory_service.repository_for_retrieval()
    assert repository is not None
    for candidate, memory in memories:
        assert repository.save_evaluation(candidate, memory) is True


def _query(**overrides) -> RetrievalQuery:
    values = {
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "keywords": [],
    }
    values.update(overrides)
    return RetrievalQuery.model_validate(values)


@pytest.fixture(autouse=True)
def clean_services(monkeypatch):
    for name in (FLAG_CALLER_REGISTRY, FLAG_DATABASE_URL, FLAG_PERSISTENCE, FLAG_ENABLED):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    operational_memory_service.reset()
    observability_service.reset()
    yield
    operational_memory_service.reset()
    observability_service.reset()


@pytest.fixture
def postgres_url() -> Iterator[str]:
    value = (os.environ.get("PEDROCORE_TEST_POSTGRES_URL") or "").strip()
    if not value:
        pytest.skip("PEDROCORE_TEST_POSTGRES_URL não configurada")
    apply_postgresql_migrations(value, MIGRATIONS)
    repository = PostgreSQLOperationalMemoryRepository(value)
    repository.clear()
    yield value
    repository.clear()


def test_query_is_structured_and_rejects_raw_prompt_fields():
    with pytest.raises(ValidationError):
        RetrievalQuery.model_validate(
            {
                "producer": "alpha-technical-tool",
                "project_id": "alpha",
                "raw_query": "dump the complete prompt",
            }
        )
    with pytest.raises(ValidationError):
        _query(max_results=6)


def test_no_results_is_explicit_and_stable():
    result = retrieval_service.retrieve(_query(keywords=["debt"]))
    assert result.status == "ok"
    assert result.items == []
    assert result.candidates == []
    assert result.policy_version == "retrieval-v1"


def test_debt_query_does_not_prioritize_auth_memory_by_project_only():
    _save(
        _memory("debt.refactor", "Technical debt refactoring backlog."),
        _memory("auth.rotation", "Authentication token rotation policy."),
    )
    result = retrieval_service.retrieve(
        _query(keywords=["debt", "refactoring"], task_type="code_maintenance")
    )
    assert [item.pattern_id for item in result.items] == ["pat_debt_refactor"]
    assert all(item.pattern_id != "pat_auth_rotation" for item in result.items)


def test_default_lifecycle_excludes_resolved_but_explicit_filter_can_include_it():
    _save(
        _memory("resolved.issue", "Resolved deployment issue.", lifecycle=MemoryLifecycle.RESOLVED)
    )
    default = retrieval_service.retrieve(_query())
    explicit = retrieval_service.retrieve(_query(lifecycles=["RESOLVED"]))
    assert default.items == []
    assert default.candidates[0].rejection_reasons == ["LIFECYCLE_NOT_REQUESTED"]
    assert [item.lifecycle for item in explicit.items] == [MemoryLifecycle.RESOLVED]


def test_anti_pattern_requires_explicit_opt_in():
    _save(
        _memory(
            "anti.retry",
            "Blind retry loops amplify failures.",
            pattern_type=PatternType.ANTI_PATTERN,
        )
    )
    blocked = retrieval_service.retrieve(_query(keywords=["retry"]))
    allowed = retrieval_service.retrieve(_query(keywords=["retry"], include_anti_patterns=True))
    assert blocked.items == []
    assert "ANTI_PATTERN_NOT_AUTHORIZED" in blocked.candidates[0].rejection_reasons
    assert allowed.items[0].pattern_type is PatternType.ANTI_PATTERN


def test_recency_confidence_and_evidence_filters_are_explainable():
    old = datetime.now(timezone.utc) - timedelta(days=60)
    _save(_memory("old.pattern", "Old operational pattern.", confidence=0.4, updated_at=old))
    result = retrieval_service.retrieve(
        _query(recency_days=30, min_confidence=0.7, min_evidence_count=4)
    )
    assert result.items == []
    reasons = result.candidates[0].rejection_reasons
    assert reasons == [
        "BELOW_MIN_CONFIDENCE",
        "BELOW_MIN_EVIDENCE",
        "OUTSIDE_RECENCY_WINDOW",
    ]


def test_result_and_context_limits_reject_remaining_candidates():
    _save(
        _memory("limit.one", "One " + "x" * 150),
        _memory("limit.two", "Two " + "y" * 150),
    )
    result = retrieval_service.retrieve(_query(max_results=1, max_context_chars=300))
    assert len(result.items) == 1
    assert result.context_chars <= 300
    assert "RESULT_LIMIT_REACHED" in result.candidates[1].rejection_reasons


def test_observability_records_ids_scores_and_rejections_without_query_or_summary(monkeypatch):
    monkeypatch.setenv(FLAG_ENABLED, "true")
    _save(_memory("observe.memory", "Sensitive business context stays out of the trace."))
    result = retrieval_service.retrieve(
        _query(query_id="qry-observe", keywords=["sensitive", "business"])
    )
    record = observability_service.get("qry-observe")
    assert record is not None
    serialized = json.dumps(record.model_dump(mode="json"), ensure_ascii=False).lower()
    assert record.result_returned["selected_memory_ids"] == [result.items[0].memory_id]
    assert "keywords" in record.removed_fields
    assert "sensitive business" not in serialized
    assert "stays out of the trace" not in serialized


def test_api_requires_project_bound_technical_auth(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    payload = _query(query_id="qry-api").model_dump(mode="json")
    unauthenticated = client.post("/api/operational-memory/retrieve", json=payload)
    authorized = client.post(
        "/api/operational-memory/retrieve",
        headers={AUTH_HEADER: API_KEY},
        json=payload,
    )
    assert unauthenticated.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json()["query_id"] == "qry-api"


def test_postgresql_fts_is_project_scoped_and_searchable(postgres_url, monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "postgresql")
    monkeypatch.setenv(FLAG_DATABASE_URL, postgres_url)
    operational_memory_service.reset()
    _save(
        _memory("postgres.debt", "Technical debt cleanup in billing."),
        _memory("postgres.auth", "Authentication hardening policy."),
    )
    result = retrieval_service.retrieve(_query(keywords=["debt", "billing"]))
    assert [item.pattern_id for item in result.items] == ["pat_postgres_debt"]
