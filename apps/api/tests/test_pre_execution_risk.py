"""Gate 8 — hybrid, non-destructive pre-execution risk analysis."""

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.operational_memory.schemas import MemoryLifecycle, PatternType
from app.modules.retrieval.schemas import RetrievalResponse, RetrievedMemory
from app.modules.retrieval.service import retrieval_service
from app.modules.report_memory.repository import ReportMemoryRepositoryError
from app.modules.risk_engine.pre_execution_schemas import RiskDimensionName
from app.modules.risk_engine.pre_execution_service import pre_execution_risk_service
from app.modules.risk_engine.schemas import RiskRequest

client = TestClient(app)
AUTH_HEADER = "X-PedroCore-Api-Key"
API_KEY = "risk-analysis-key-synthetic"


def _payload(**overrides) -> dict:
    values = {
        "request_id": "pre-risk-001",
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "request_text": "Change the billing module within the approved scope.",
        "environment": "development",
        "agent_id": "codex-local",
        "permissions": ["read:billing", "write:billing"],
        "context": {
            "allowed_scope": ["module:billing", "file:billing/service.py"],
            "forbidden_scope": ["module:auth"],
            "known_files": ["billing/service.py"],
            "known_modules": ["billing"],
            "database": "billing_test",
            "user_scope": "synthetic-users",
            "external_integrations": ["billing-sandbox"],
            "constraints": ["local only"],
            "acceptance_criteria": ["tests pass"],
            "required_tests": ["billing unit"],
            "rollback_plan_present": True,
        },
        "requested_operation": {
            "kind": "WRITE",
            "targets": ["module:billing"],
            "expected_changes": ["bounded edit"],
        },
    }
    values.update(overrides)
    return values


def _empty_retrieval(query) -> RetrievalResponse:
    return RetrievalResponse(
        query_id=query.query_id or "query",
        project_id=query.project_id,
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
def no_historical_memory(monkeypatch):
    monkeypatch.setattr(retrieval_service, "retrieve", _empty_retrieval)


@pytest.mark.parametrize(
    ("overrides", "reason_code"),
    [
        (
            {
                "request_text": "Run database migration.",
                "requested_operation": {"kind": "MIGRATE", "targets": ["database:billing"]},
            },
            "DATABASE_MIGRATION",
        ),
        ({"request_text": "Alter table schema change."}, "SCHEMA_CHANGE"),
        ({"request_text": "Change auth authorization rules."}, "AUTH_AUTHZ_CHANGE"),
        ({"request_text": "Update .env secret token."}, "SECRETS_OR_ENV"),
        ({"request_text": "Edit CI/CD workflow pipeline."}, "CI_CD_CHANGE"),
        (
            {
                "request_text": "Delete billing data.",
                "requested_operation": {"kind": "DELETE", "targets": ["module:billing"]},
            },
            "DELETE_OPERATION",
        ),
        ({"request_text": "Bulk mass change all files."}, "MASS_FILE_CHANGE"),
        ({"request_text": "Change security policy and firewall."}, "SECURITY_POLICY_CHANGE"),
        ({"environment": "production"}, "PRODUCTION_CONFIGURATION"),
        ({"request_text": "Grant permission and privilege role."}, "PERMISSION_CHANGE"),
        (
            {
                "request_text": "Send a third-party webhook.",
                "requested_operation": {
                    "kind": "EXECUTE",
                    "targets": ["module:billing"],
                    "external_effects": True,
                },
            },
            "EXTERNAL_INTEGRATION",
        ),
    ],
)
def test_deterministic_rule_catalog_covers_initial_high_risk_operations(
    overrides, reason_code
):
    analysis = pre_execution_risk_service.analyze(
        RiskRequest.model_validate(_payload(**overrides))
    )
    assert reason_code in {item.reason_code for item in analysis.deterministic_rules}
    assert any(item.reason_code == reason_code for item in analysis.evidence)


def test_dimensions_remain_separate_instead_of_becoming_one_score():
    request = RiskRequest.model_validate(
        _payload(
            request_text="Delete data during a schema migration with auth policy changes.",
            requested_operation={
                "kind": "MIGRATE",
                "targets": ["module:billing", "database:billing"],
                "destructive": True,
            },
        )
    )
    analysis = pre_execution_risk_service.analyze(request)
    dimensions = {item.dimension: item for item in analysis.risk_dimensions}
    assert set(dimensions) == set(RiskDimensionName)
    assert dimensions[RiskDimensionName.DATA].score > 0
    assert dimensions[RiskDimensionName.SECURITY].score > 0
    assert dimensions[RiskDimensionName.MIGRATION].score > 0
    assert not hasattr(analysis, "risk_score")


def test_blast_radius_exposes_each_affected_boundary():
    request = RiskRequest.model_validate(
        _payload(
            request_text="Change auth permission through external integration.",
            environment="production",
            requested_operation={
                "kind": "WRITE",
                "targets": ["module:billing", "file:billing/service.py"],
                "external_effects": True,
            },
        )
    )
    radius = pre_execution_risk_service.analyze(request).blast_radius
    assert radius.files == ["file:billing/service.py"]
    assert radius.modules == ["module:billing"]
    assert radius.users == ["synthetic-users"]
    assert radius.permissions == ["read:billing", "write:billing"]
    assert radius.environments == ["production"]
    assert radius.external_integrations == ["billing-sandbox"]
    assert "AUTH_AUTHZ_CHANGE" in radius.security_boundaries


def test_relevant_scenarios_are_analytical_dry_runs_only():
    """Stage R5: os seis cenarios base mais os relevantes ao payload.

    Antes do R5 a lista era fixa. Agora cenario condicional so aparece quando
    o FATO correspondente existe — este payload declara `required_tests` e
    `external_integrations`, entao os dois cenarios correspondentes entram.
    """
    analysis = pre_execution_risk_service.analyze(
        RiskRequest.model_validate(_payload())
    )
    assert [item.scenario for item in analysis.simulations] == [
        "success",
        "partial_failure",
        "scope_deviation",
        "dependency_failure",
        "rollback_requirement",
        "security_impact",
        "test_failure",
        "external_service_failure",
    ]
    assert all(item.mode == "analytical_dry_run" for item in analysis.simulations)
    assert all(item.target_operation_executed is False for item in analysis.simulations)


def test_operational_memory_is_consumed_as_bounded_historical_evidence(monkeypatch):
    fixed = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def historical(query):
        return RetrievalResponse(
            query_id=query.query_id,
            project_id="alpha",
            items=[
                RetrievedMemory(
                    memory_id="memory-risk-1",
                    pattern_id="pattern-risk-1",
                    pattern_type=PatternType.RISK_PATTERN,
                    lifecycle=MemoryLifecycle.ACTIVE,
                    task_type="migration",
                    summary="Synthetic historical risk.",
                    confidence=0.82,
                    evidence_count=4,
                    relevance_score=0.91,
                    policy_version="operational-memory-v1",
                    updated_at=fixed,
                )
            ],
        )

    monkeypatch.setattr(retrieval_service, "retrieve", historical)
    analysis = pre_execution_risk_service.analyze(
        RiskRequest.model_validate(_payload(request_text="Run billing migration."))
    )
    history = analysis.historical_evidence
    assert history.source == "operational_memory"
    assert history.sample_size == 1
    assert history.items[0].memory_id == "memory-risk-1"
    assert any(item.source == "operational_memory" for item in analysis.evidence)


def test_analysis_is_reproducible_and_never_executes_or_calls_provider():
    request = RiskRequest.model_validate(_payload())
    first = pre_execution_risk_service.analyze(request)
    second = pre_execution_risk_service.analyze(request)
    assert first == second
    assert first.target_operation_executed is False
    assert first.provider_called is False
    assert first.semantic_analysis.provider_called is False
    assert first.operational_memory_created is False


def test_api_requires_project_bound_technical_identity(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    denied = client.post("/api/risk/analyze", json=_payload())
    accepted = client.post(
        "/api/risk/analyze",
        headers={AUTH_HEADER: API_KEY},
        json=_payload(),
    )
    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["policy_version"] == "pre-execution-risk-v1"


def test_api_fails_closed_when_historical_persistence_is_unavailable(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())

    def unavailable(_query):
        raise ReportMemoryRepositoryError("database detail must remain private")

    monkeypatch.setattr(retrieval_service, "retrieve", unavailable)
    response = client.post(
        "/api/risk/analyze",
        headers={AUTH_HEADER: API_KEY},
        json=_payload(),
    )
    assert response.status_code == 503
    assert response.json()["error_code"] == "OPERATIONAL_MEMORY_PERSISTENCE_UNAVAILABLE"
    assert "database detail" not in response.text
