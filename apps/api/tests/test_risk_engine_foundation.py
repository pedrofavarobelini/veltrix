"""Gate 7 — deterministic and non-executing Risk Engine foundation."""

import json

from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.risk_engine.schemas import OperationKind, RiskRequest, RiskSeverity
from app.modules.risk_engine.service import risk_engine_foundation_service

client = TestClient(app)
AUTH_HEADER = "X-PedroCore-Api-Key"
API_KEY = "risk-foundation-key-synthetic"


def _payload(**overrides) -> dict:
    values = {
        "schema_version": "1.0",
        "request_id": "risk-request-001",
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "request_text": "Alterar o módulo billing e executar os testes unitários.",
        "environment": "development",
        "agent_id": "codex-local",
        "permissions": ["read:billing", "write:billing"],
        "context": {
            "allowed_scope": ["module:billing"],
            "forbidden_scope": ["module:auth"],
            "known_modules": ["billing"],
            "constraints": ["no production", "no external calls"],
            "acceptance_criteria": ["unit tests pass"],
            "required_tests": ["billing unit"],
            "rollback_plan_present": True,
        },
        "requested_operation": {
            "kind": "WRITE",
            "targets": ["module:billing"],
            "expected_changes": ["bounded source edit"],
        },
    }
    values.update(overrides)
    return values


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


def test_controlled_input_is_structured_and_fully_reproducible():
    request = RiskRequest.model_validate(_payload())
    first = risk_engine_foundation_service.analyze(request)
    second = risk_engine_foundation_service.analyze(request)
    assert first == second
    assert first.assessment_id.startswith("risk_")
    assert first.intent.operation is OperationKind.WRITE
    assert first.scope.bounded is True
    assert first.prompt_quality.score == 1.0
    assert first.signals == []


def test_foundation_never_executes_target_calls_provider_or_creates_memory():
    assessment = risk_engine_foundation_service.analyze(
        RiskRequest.model_validate(_payload())
    )
    assert assessment.target_operation_executed is False
    assert assessment.provider_called is False
    assert assessment.operational_memory_created is False
    serialized = json.dumps(assessment.model_dump(mode="json"), ensure_ascii=False)
    assert "Alterar o módulo billing" not in serialized


def test_intent_conflict_is_high_risk_and_deterministic():
    payload = _payload(request_text="Read and inspect the billing module only.")
    request = RiskRequest.model_validate(payload)
    assessment = risk_engine_foundation_service.analyze(request)
    assert assessment.intent.inferred_operation is OperationKind.READ
    assert assessment.intent.intent_consistent is False
    assert assessment.ambiguity.ambiguity_codes == ["TEXT_OPERATION_CONFLICT"]
    signal = next(item for item in assessment.signals if item.code == "INTENT_CONFLICT")
    assert signal.severity is RiskSeverity.HIGH


def test_context_resolution_reports_missing_permission_scope_and_database():
    payload = _payload(
        permissions=[],
        context={
            "allowed_scope": [],
            "constraints": [],
            "acceptance_criteria": [],
            "required_tests": [],
        },
        requested_operation={
            "kind": "MIGRATE",
            "targets": ["database:primary"],
        },
    )
    assessment = risk_engine_foundation_service.analyze(RiskRequest.model_validate(payload))
    assert assessment.resolved_context.missing_context == [
        "permissions",
        "allowed_scope",
        "database",
    ]
    assert assessment.ambiguity.ambiguous is True
    assert assessment.scope.unknown_targets == ["database:primary"]
    assert assessment.prompt_quality.score < 0.5


def test_scope_analysis_separates_forbidden_and_outside_targets():
    payload = _payload(
        requested_operation={
            "kind": "WRITE",
            "targets": ["module:billing", "module:auth", "module:unknown"],
        }
    )
    assessment = risk_engine_foundation_service.analyze(RiskRequest.model_validate(payload))
    assert assessment.scope.targets_in_scope == ["module:billing"]
    assert assessment.scope.forbidden_targets == ["module:auth"]
    assert assessment.scope.targets_outside_scope == ["module:auth", "module:unknown"]
    assert {item.code for item in assessment.signals} >= {
        "FORBIDDEN_SCOPE_REQUESTED",
        "SCOPE_UNBOUNDED",
    }


def test_destructive_external_intent_emits_independent_signals():
    payload = _payload(
        request_text="Delete remote billing records.",
        context={
            **_payload()["context"],
            "external_integrations": ["billing-sandbox"],
        },
        requested_operation={
            "kind": "DELETE",
            "targets": ["module:billing"],
            "destructive": True,
            "external_effects": True,
        },
    )
    assessment = risk_engine_foundation_service.analyze(RiskRequest.model_validate(payload))
    codes = {item.code for item in assessment.signals}
    assert "DESTRUCTIVE_INTENT" in codes
    assert "EXTERNAL_EFFECTS" in codes


def test_api_requires_project_bound_technical_identity(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    denied = client.post("/api/risk/foundation/analyze", json=_payload())
    accepted = client.post(
        "/api/risk/foundation/analyze",
        headers={AUTH_HEADER: API_KEY},
        json=_payload(),
    )
    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["target_operation_executed"] is False
