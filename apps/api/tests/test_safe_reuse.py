"""Gate 6 — conservative Safe Reuse candidate classification."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.operational_memory.schemas import (
    ConfidenceBreakdown,
    MemoryLifecycle,
    OperationalMemoryEntry,
    OperationalPattern,
    PatternType,
)
from app.modules.operational_memory.service import operational_memory_service
from app.modules.report_memory.service import FLAG_PERSISTENCE
from app.modules.safe_reuse.schemas import (
    ReuseEvaluationRequest,
    ReuseMode,
)
from app.modules.safe_reuse.service import safe_reuse_service

client = TestClient(app)
AUTH_HEADER = "X-PedroCore-Api-Key"
API_KEY = "safe-reuse-key-synthetic"


def _signature(character: str) -> str:
    return "sha256:" + character * 64


def _fingerprint(**overrides) -> dict:
    values = {
        "input_signature": _signature("a"),
        "context_signature": _signature("b"),
        "data_signature": _signature("c"),
        "project_id": "alpha",
        "user_scope_signature": _signature("d"),
        "family_scope_signature": _signature("e"),
        "permissions": ["read:reports", "write:plans"],
        "environment": "development",
        "temporal_state_signature": _signature("f"),
        "policy_version": "policy-7",
        "dependency_version": "deps-12",
    }
    values.update(overrides)
    return values


def _request(mode: str = "DIRECT_REUSE", **candidate_overrides) -> ReuseEvaluationRequest:
    now = datetime.now(timezone.utc)
    candidate = {
        "candidate_id": "candidate-1",
        "proposed_mode": mode,
        "source_fingerprint": _fingerprint(),
        "validation_status": "VALIDATED",
        "validation_signature": _signature("9"),
        "validated_at": now.isoformat(),
        "valid_until": (now + timedelta(hours=1)).isoformat(),
    }
    candidate.update(candidate_overrides)
    return ReuseEvaluationRequest.model_validate(
        {
            "evaluation_id": "reuse-evaluation-1",
            "producer": "alpha-technical-tool",
            "project_id": "alpha",
            "current_fingerprint": _fingerprint(),
            "candidate": candidate,
        }
    )


def _memory(memory_id: str, pattern_type: PatternType) -> OperationalMemoryEntry:
    now = datetime.now(timezone.utc)
    return OperationalMemoryEntry(
        memory_id=memory_id,
        project_id="alpha",
        pattern=OperationalPattern(
            pattern_id=f"pattern-{memory_id}",
            pattern_type=pattern_type,
            pattern_key=f"safe.{memory_id}",
            task_type="safe_reuse",
            summary="Bounded synthetic memory.",
        ),
        confidence=0.8,
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
        lifecycle=MemoryLifecycle.ACTIVE,
        sample_size=3,
        policy_version="operational-memory-v1",
        created_at=now,
        updated_at=now,
        retention_until=now + timedelta(days=365),
    )


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


@pytest.fixture(autouse=True)
def clean_services(monkeypatch):
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    operational_memory_service.reset()
    yield
    operational_memory_service.reset()


def test_direct_reuse_is_only_a_candidate_and_never_bypasses_provider():
    decision = safe_reuse_service.evaluate(_request())
    assert decision.mode is ReuseMode.DIRECT_REUSE
    assert decision.provider_bypass is False
    assert decision.reusable_response_returned is False
    assert "STRONG_EQUIVALENCE_CONFIRMED" in decision.reason_codes
    assert "PROVIDER_BYPASS_FORBIDDEN" in decision.reason_codes
    assert "response" not in decision.model_dump(mode="json")


@pytest.mark.parametrize(
    ("dimension", "changed"),
    [
        ("input_signature", _signature("1")),
        ("context_signature", _signature("2")),
        ("data_signature", _signature("3")),
        ("project_id", "beta"),
        ("user_scope_signature", _signature("4")),
        ("family_scope_signature", _signature("5")),
        ("permissions", ["read:reports"]),
        ("environment", "production"),
        ("temporal_state_signature", _signature("6")),
        ("policy_version", "policy-8"),
        ("dependency_version", "deps-13"),
    ],
)
def test_direct_reuse_invalidates_every_strong_equivalence_dimension(dimension, changed):
    request = _request(source_fingerprint=_fingerprint(**{dimension: changed}))
    decision = safe_reuse_service.evaluate(request)
    assert decision.mode is ReuseMode.NO_REUSE
    assert decision.invalidated_dimensions == [dimension]
    assert decision.provider_bypass is False


def test_template_reuse_allows_new_content_but_preserves_scope_and_validation():
    source = _fingerprint(
        input_signature=_signature("1"),
        context_signature=_signature("2"),
        data_signature=_signature("3"),
    )
    decision = safe_reuse_service.evaluate(
        _request(
            "TEMPLATE_REUSE",
            source_fingerprint=source,
            template_id="qa-report-template",
            template_version="2",
        )
    )
    assert decision.mode is ReuseMode.TEMPLATE_REUSE
    assert decision.provider_bypass is False


def test_unknown_or_expired_validation_fails_closed():
    unknown = safe_reuse_service.evaluate(_request(validation_status="UNKNOWN"))
    expired = safe_reuse_service.evaluate(
        _request(valid_until=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())
    )
    assert unknown.mode is ReuseMode.NO_REUSE
    assert unknown.reason_codes == ["VALIDATION_REQUIRED"]
    assert expired.mode is ReuseMode.NO_REUSE
    assert expired.reason_codes == ["VALIDATION_EXPIRED"]


def test_knowledge_and_anti_pattern_reuse_resolve_operational_memory(monkeypatch):
    knowledge = _memory("memory-knowledge", PatternType.PROJECT_PATTERN)
    anti = _memory("memory-anti", PatternType.ANTI_PATTERN)
    repository = operational_memory_service.repository_for_retrieval()
    assert repository is not None
    monkeypatch.setattr(
        repository,
        "get_memory",
        lambda project_id, memory_id: {
            "memory-knowledge": knowledge,
            "memory-anti": anti,
        }.get(memory_id)
        if project_id == "alpha"
        else None,
    )

    knowledge_decision = safe_reuse_service.evaluate(
        _request("KNOWLEDGE_REUSE", memory_id="memory-knowledge")
    )
    anti_decision = safe_reuse_service.evaluate(
        _request("ANTI_PATTERN", memory_id="memory-anti")
    )
    wrong_mode = safe_reuse_service.evaluate(
        _request("KNOWLEDGE_REUSE", memory_id="memory-anti")
    )

    assert knowledge_decision.mode is ReuseMode.KNOWLEDGE_REUSE
    assert anti_decision.mode is ReuseMode.ANTI_PATTERN
    assert wrong_mode.mode is ReuseMode.NO_REUSE
    assert wrong_mode.reason_codes == ["ANTI_PATTERN_MODE_REQUIRED"]


def test_explicit_no_reuse_remains_conservative():
    decision = safe_reuse_service.evaluate(_request("NO_REUSE"))
    assert decision.mode is ReuseMode.NO_REUSE
    assert decision.reason_codes == ["NO_REUSE_REQUESTED"]


def test_api_requires_bound_technical_identity(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    payload = _request().model_dump(mode="json")
    denied = client.post("/api/safe-reuse/evaluate", json=payload)
    accepted = client.post(
        "/api/safe-reuse/evaluate",
        headers={AUTH_HEADER: API_KEY},
        json=payload,
    )
    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["provider_bypass"] is False
