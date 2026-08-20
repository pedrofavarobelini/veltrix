"""Gate 11 — Operational Memory history and reproducible risk benchmark."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

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
from app.modules.retrieval.schemas import RetrievalResponse, RetrievedMemory
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_engine.historical_schemas import (
    BenchmarkCase,
    HistoricalBenchmarkRequest,
    HistoricalRiskQuery,
    HistoricalRiskSummary,
    HistoricalSample,
)
from app.modules.risk_engine.historical_service import historical_risk_service
from app.modules.risk_engine.schemas import RiskRequest

client = TestClient(app)
AUTH_HEADER = "X-PedroCore-Api-Key"
API_KEY = "historical-risk-key-synthetic"
NOW = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)


def _memory(
    suffix: str,
    pattern_type: PatternType,
    *,
    confidence: float = 0.8,
    lifecycle: MemoryLifecycle = MemoryLifecycle.ACTIVE,
    task_type: str = "post_execution_verification",
    updated_at: datetime = NOW,
) -> OperationalMemoryEntry:
    return OperationalMemoryEntry(
        memory_id=f"memory-{suffix}",
        project_id="alpha",
        pattern=OperationalPattern(
            pattern_id=f"pattern-{suffix}",
            pattern_type=pattern_type,
            pattern_key=f"history.{suffix}",
            task_type=task_type,
            summary="Synthetic historical pattern.",
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
        sample_size=3,
        policy_version="operational-memory-v1",
        created_at=updated_at,
        updated_at=updated_at,
        retention_until=updated_at + timedelta(days=365),
    )


def _query(**overrides) -> HistoricalRiskQuery:
    values = {
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "window_start": NOW - timedelta(days=30),
        "window_end": NOW + timedelta(days=1),
    }
    values.update(overrides)
    return HistoricalRiskQuery.model_validate(values)


def _risk_request(case_id: str, kind: str, target: str, text: str) -> RiskRequest:
    permission = kind.lower() + ":scope"
    return RiskRequest.model_validate(
        {
            "request_id": f"request-{case_id}",
            "producer": "alpha-technical-tool",
            "project_id": "alpha",
            "request_text": text,
            "environment": "development",
            "agent_id": "codex-local",
            "permissions": [permission],
            "context": {
                "allowed_scope": [target],
                "constraints": ["fixture only"],
                "acceptance_criteria": ["fixture result"],
                "required_tests": ["fixture test"],
                "rollback_plan_present": True,
            },
            "requested_operation": {"kind": kind, "targets": [target]},
        }
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


def test_history_records_window_filters_outcomes_confidence_and_policy(monkeypatch):
    memories = [
        _memory("success", PatternType.SUCCESS_PATTERN),
        _memory("risk", PatternType.RISK_PATTERN, confidence=0.9),
        _memory("mixed", PatternType.RISK_PATTERN),
        _memory("unknown", PatternType.FAILURE_PATTERN),
        _memory("old", PatternType.RISK_PATTERN, updated_at=NOW - timedelta(days=90)),
    ]
    repository = SimpleNamespace(list_memory=lambda project_id, limit: memories)
    monkeypatch.setattr(
        operational_memory_service,
        "repository_for_retrieval",
        lambda: repository,
    )
    policies = {
        "memory-success": ["pre-execution-risk-v1"],
        "memory-risk": ["pre-execution-risk-v1"],
        "memory-mixed": ["pre-execution-risk-v1", "pre-execution-risk-v2"],
        "memory-unknown": [],
        "memory-old": ["pre-execution-risk-v1"],
    }
    monkeypatch.setattr(
        historical_risk_service,
        "_risk_policies",
        lambda _project, memory: policies[memory.memory_id],
    )
    summary = historical_risk_service.summarize(_query(min_confidence=0.7))
    assert summary.sample_size == 2
    assert summary.outcomes == {"risk": 1, "success": 1}
    assert summary.average_confidence == 0.85
    assert summary.filters["min_confidence"] == 0.7
    assert summary.risk_policy_versions == ["pre-execution-risk-v1"]
    assert summary.generalizable is False
    assert summary.small_sample_warning is True
    assert {item.reason_code for item in summary.excluded_samples} == {
        "INCOMPATIBLE_POLICY_MIX",
        "RISK_POLICY_UNKNOWN",
    }


def test_thirty_compatible_samples_are_the_minimum_for_generalization(monkeypatch):
    memories = [_memory(f"success-{index}", PatternType.SUCCESS_PATTERN) for index in range(30)]
    repository = SimpleNamespace(list_memory=lambda project_id, limit: memories)
    monkeypatch.setattr(
        operational_memory_service,
        "repository_for_retrieval",
        lambda: repository,
    )
    monkeypatch.setattr(
        historical_risk_service,
        "_risk_policies",
        lambda _project, _memory: ["pre-execution-risk-v1"],
    )
    summary = historical_risk_service.summarize(_query())
    assert summary.sample_size == 30
    assert summary.generalizable is True
    assert summary.small_sample_warning is False


def test_disabled_operational_memory_returns_empty_non_training_summary(monkeypatch):
    monkeypatch.setattr(
        operational_memory_service,
        "repository_for_retrieval",
        lambda: None,
    )
    summary = historical_risk_service.summarize(_query())
    assert summary.status == "disabled"
    assert summary.sample_size == 0
    assert summary.training_performed is False


def test_benchmark_compares_four_strategies_and_prioritizes_severe_false_negatives(
    monkeypatch,
):
    samples = [
        HistoricalSample(
            memory_id="memory-risk",
            pattern_type=PatternType.RISK_PATTERN,
            lifecycle=MemoryLifecycle.ACTIVE,
            task_type="post_execution_verification",
            confidence=0.9,
            evidence_count=5,
            updated_at=NOW,
            operational_memory_policy_version="operational-memory-v1",
            risk_policy_versions=["pre-execution-risk-v1"],
            outcome_class="risk",
        ),
        HistoricalSample(
            memory_id="memory-success",
            pattern_type=PatternType.SUCCESS_PATTERN,
            lifecycle=MemoryLifecycle.ACTIVE,
            task_type="post_execution_verification",
            confidence=0.9,
            evidence_count=5,
            updated_at=NOW,
            operational_memory_policy_version="operational-memory-v1",
            risk_policy_versions=["pre-execution-risk-v1"],
            outcome_class="success",
        ),
    ]
    summary = HistoricalRiskSummary(
        project_id="alpha",
        risk_policy_versions=["pre-execution-risk-v1"],
        window_start=NOW - timedelta(days=30),
        window_end=NOW,
        sample_size=2,
        excluded_count=0,
        outcomes={"risk": 1, "success": 1},
        average_confidence=0.9,
        samples=samples,
    )
    monkeypatch.setattr(historical_risk_service, "summarize", lambda _query: summary)

    def retrieve(query):
        target = " ".join(query.keywords)
        risk = "billing" in target or "delete" in target
        return RetrievalResponse(
            query_id=query.query_id,
            project_id="alpha",
            items=[
                RetrievedMemory(
                    memory_id="memory-risk" if risk else "memory-success",
                    pattern_id="pattern-history",
                    pattern_type=(PatternType.RISK_PATTERN if risk else PatternType.SUCCESS_PATTERN),
                    lifecycle=MemoryLifecycle.ACTIVE,
                    task_type="post_execution_verification",
                    summary="Synthetic benchmark history.",
                    confidence=0.9,
                    evidence_count=5,
                    relevance_score=0.9,
                    policy_version="operational-memory-v1",
                    updated_at=NOW,
                )
            ],
        )

    monkeypatch.setattr(retrieval_service, "retrieve", retrieve)
    cases = [
        BenchmarkCase(
            case_id="vague-severe",
            request=_risk_request(
                "vague-severe",
                "WRITE",
                "module:billing",
                "Change billing within the approved fixture.",
            ),
            actual_risk=True,
            severe_actual=True,
        ),
        BenchmarkCase(
            case_id="safe-read",
            request=_risk_request(
                "safe-read", "READ", "module:docs", "Read docs in the approved fixture."
            ),
            actual_risk=False,
        ),
        BenchmarkCase(
            case_id="delete-risk",
            request=_risk_request(
                "delete-risk", "DELETE", "module:billing", "Delete billing fixture data."
            ),
            actual_risk=True,
            severe_actual=True,
        ),
    ]
    request = HistoricalBenchmarkRequest(
        producer="alpha-technical-tool",
        project_id="alpha",
        window_start=NOW - timedelta(days=30),
        window_end=NOW,
        cases=cases,
    )
    first = historical_risk_service.benchmark(request)
    second = historical_risk_service.benchmark(request)
    assert first == second
    assert [item.strategy for item in first.strategies] == [
        "deterministic_only",
        "semantic_only",
        "history_only",
        "hybrid",
    ]
    deterministic = first.strategies[0]
    hybrid = first.strategies[-1]
    assert deterministic.severe_false_negative == 1
    assert hybrid.severe_false_negative == 0
    assert hybrid.recall == 1.0
    assert first.recommended_strategy == "hybrid"
    assert first.risk_policy_version == "pre-execution-risk-v1"
    assert first.training_performed is False


def test_benchmark_schema_rejects_cross_project_cases():
    case = BenchmarkCase(
        case_id="beta-case",
        request=_risk_request("beta", "READ", "module:docs", "Read docs.").model_copy(
            update={"project_id": "beta"}
        ),
        actual_risk=False,
    )
    with pytest.raises(ValueError):
        HistoricalBenchmarkRequest(
            producer="alpha-technical-tool",
            project_id="alpha",
            window_start=NOW - timedelta(days=1),
            window_end=NOW,
            cases=[case],
        )


def test_history_api_requires_project_bound_identity(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    monkeypatch.setattr(
        operational_memory_service,
        "repository_for_retrieval",
        lambda: None,
    )
    payload = _query().model_dump(mode="json")
    denied = client.post("/api/risk/history/query", json=payload)
    accepted = client.post(
        "/api/risk/history/query",
        headers={AUTH_HEADER: API_KEY},
        json=payload,
    )
    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["training_performed"] is False
