"""Gate 10 — contract×execution, predicted×actual, existing QA and V2 outcome."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.operational_memory.service import operational_memory_service
from app.modules.report_memory.service import FLAG_PERSISTENCE, report_memory_service
from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_engine.execution_contract_schemas import (
    HumanOverrideRequest,
    HumanReviewDecision,
)
from app.modules.risk_engine.execution_contract_service import (
    FLAG_CONTRACT_SIGNING_KEY,
    FLAG_REVIEWER_IDS,
    execution_contract_service,
)
from app.modules.risk_engine.post_execution_schemas import ExecutionEvidence
from app.modules.risk_engine.post_execution_service import post_execution_service
from app.modules.risk_engine.schemas import RiskRequest

client = TestClient(app)
AUTH_HEADER = "X-PedroCore-Api-Key"
API_KEY = "post-execution-alpha-key-synthetic"
SIGNING_KEY = "post-execution-signing-key-with-at-least-32-characters"
DIFF_SIGNATURE = "sha256:" + "a" * 64


def _request(request_id: str = "risk-before-001") -> RiskRequest:
    return RiskRequest.model_validate(
        {
            "request_id": request_id,
            "producer": "alpha-technical-tool",
            "project_id": "alpha",
            "request_text": "Change billing service and run its unit tests.",
            "environment": "development",
            "agent_id": "codex-local",
            "permissions": ["read:billing", "write:billing"],
            "context": {
                "allowed_scope": ["module:billing", "file:billing/service.py"],
                "forbidden_scope": ["module:auth", "file:auth/service.py"],
                "known_files": ["billing/service.py"],
                "known_modules": ["billing"],
                "constraints": ["local only"],
                "acceptance_criteria": ["tests pass"],
                "required_tests": ["billing unit"],
                "rollback_plan_present": True,
            },
            "requested_operation": {
                "kind": "WRITE",
                "targets": ["module:billing", "file:billing/service.py"],
                "expected_changes": ["bounded edit"],
                "commands": ["pytest billing"],
            },
        }
    )


def _caller() -> AuthenticatedCallerContext:
    return AuthenticatedCallerContext(
        credential_id="alpha-technical-tool",
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="development",
        identity_strength=IdentityStrength.REGISTERED,
        authenticated=True,
        project_id="alpha",
        allowed_origins=("alpha",),
    )


def _evidence(evidence_id: str = "execution-evidence-001", **overrides) -> ExecutionEvidence:
    request = overrides.pop("request", _request())
    contract = overrides.pop("contract", execution_contract_service.issue(request))
    started = datetime.now(timezone.utc)
    values = {
        "evidence_id": evidence_id,
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "contract": contract,
        "current_request": request,
        "started_at": started,
        "finished_at": started + timedelta(seconds=2),
        "files_changed": ["billing/service.py"],
        "diff": {
            "diff_signature": DIFF_SIGNATURE,
            "files_count": 1,
            "additions": 8,
            "deletions": 2,
        },
        "commands": [
            {"command_id": "cmd-test-billing", "command": "pytest billing", "exit_code": 0}
        ],
        "tests": [
            {
                "suite": "billing unit",
                "status": "passed",
                "passed": 3,
                "failed": 0,
                "skipped": 0,
            }
        ],
        "security_results": [
            {
                "scanner": "local-security",
                "status": "passed",
                "critical": 0,
                "high": 0,
            }
        ],
        "scope_changes": ["module:billing"],
    }
    values.update(overrides)
    return ExecutionEvidence.model_validate(values)


def _empty_retrieval(query) -> RetrievalResponse:
    return RetrievalResponse(query_id=query.query_id, project_id=query.project_id)


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
def configured(monkeypatch):
    monkeypatch.setenv(FLAG_CONTRACT_SIGNING_KEY, SIGNING_KEY)
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.setattr(retrieval_service, "retrieve", _empty_retrieval)
    report_memory_service.reset()
    operational_memory_service.reset()
    yield
    report_memory_service.reset()
    operational_memory_service.reset()


def test_success_traces_prompt_to_v2_outcome_and_existing_qa():
    outcome = post_execution_service.process(_evidence(), _caller())
    assert outcome.status == "passed"
    assert outcome.contract_valid is True
    assert outcome.comparison.reason_codes == []
    assert outcome.qa.analysis_source == "local_text_heuristic"
    assert outcome.qa_release_gate.can_advance is True
    assert outcome.execution_outcome_report.report_type.value == "execution_outcome"
    assert outcome.execution_outcome_report.schema_version == "2.0"
    assert outcome.report_persisted is True
    assert outcome.operational_memory.candidate_id is not None
    assert outcome.trace == [
        "risk-before-001",
        outcome.risk_analysis_id,
        outcome.contract_id,
        "execution-evidence-001",
        outcome.outcome_id,
        outcome.execution_outcome_report.report_id,
    ]
    assert outcome.target_operation_executed_by_risk_engine is False
    assert outcome.provider_called_by_risk_engine is False


def test_all_post_execution_deviations_are_detected_independently():
    evidence = _evidence(
        files_changed=["billing/service.py", "auth/service.py"],
        commands=[
            {"command_id": "cmd-forbidden", "command": "rm forbidden", "exit_code": 0}
        ],
        tests=[
            {
                "suite": "billing unit",
                "status": "failed",
                "passed": 2,
                "failed": 1,
            }
        ],
        security_results=[
            {
                "scanner": "local-security",
                "status": "failed",
                "critical": 1,
                "high": 0,
            }
        ],
        migration_results=[
            {
                "migration_id": "migration-1",
                "status": "rolled_back",
                "rollback_performed": True,
            }
        ],
        scope_changes=["module:billing", "module:auth"],
        unexpected_effects=["unexpected-network-effect"],
    )
    outcome = post_execution_service.process(evidence, _caller())
    assert outcome.status == "failed"
    assert set(outcome.comparison.reason_codes) == {
        "UNEXPECTED_FILES",
        "SCOPE_DEVIATION",
        "FORBIDDEN_OPERATIONS",
        "FAILED_TESTS",
        "SECURITY_FINDINGS",
        "MIGRATION_INCIDENTS",
        "UNEXPECTED_EFFECTS",
    }
    assert outcome.qa_release_gate.can_advance is False
    assert outcome.predicted_vs_actual.unpredicted_issue_detected is True


def test_missing_diff_is_explicit_and_not_inferred_from_file_list():
    outcome = post_execution_service.process(_evidence(diff=None), _caller())
    assert outcome.status == "failed"
    assert "DIFF_EVIDENCE_MISSING" in outcome.comparison.reason_codes


def test_tampered_or_review_required_contract_cannot_be_used():
    request = _request()
    contract = execution_contract_service.issue(request)
    tampered = contract.model_copy(update={"allowed_scope": ["module:auth"]})
    outcome = post_execution_service.process(
        _evidence(contract=tampered, request=request),
        _caller(),
    )
    assert outcome.status == "blocked"
    assert outcome.contract_valid is False
    assert "EXECUTION_CONTRACT_NOT_USABLE" in outcome.predicted_vs_actual.actual_issue_codes


def test_signed_human_review_continues_trace_without_hiding_original_gate(monkeypatch):
    monkeypatch.setenv(FLAG_REVIEWER_IDS, "alpha-technical-tool")
    request = _request()
    request = request.model_copy(
        update={"request_text": "Change CI/CD workflow and run its unit tests."}
    )
    contract = execution_contract_service.issue(request)
    review = execution_contract_service.override(
        HumanOverrideRequest(
            producer=request.producer,
            contract=contract,
            current_request=request,
            decision=HumanReviewDecision.APPROVE,
            reason="Reviewed synthetic CI controls before local execution.",
        ),
        _caller(),
    )
    outcome = post_execution_service.process(
        _evidence(request=request, contract=contract, human_review=review),
        _caller(),
    )
    assert contract.gate.value == "REVIEW_REQUIRED"
    assert outcome.effective_gate.value == "PASS_WITH_WARNINGS"
    assert outcome.status == "passed"


def test_three_consistent_outcomes_feed_existing_operational_memory():
    results = [
        post_execution_service.process(
            _evidence(
                evidence_id=f"execution-evidence-{index}",
                request=_request(request_id=f"risk-before-{index}"),
            ),
            _caller(),
        )
        for index in range(3)
    ]
    assert all(item.operational_memory.candidate_id for item in results)
    final = results[-1].operational_memory
    assert final.memory_id is not None
    assert final.lifecycle == "ACTIVE"


def test_duplicate_evidence_is_idempotent_for_report_and_candidate():
    evidence = _evidence()
    first = post_execution_service.process(evidence, _caller())
    second = post_execution_service.process(evidence, _caller())
    assert first.outcome_id == second.outcome_id
    assert second.report_duplicate is True
    assert second.operational_memory.duplicate is True


def test_input_schema_rejects_forged_outcome_and_invalid_chronology():
    evidence = _evidence().model_dump(mode="json")
    evidence["outcome"] = "passed"
    response = client.post("/api/risk/execution-outcomes", json=evidence)
    assert response.status_code == 422
    evidence.pop("outcome")
    evidence["finished_at"] = "2020-01-01T00:00:00Z"
    response = client.post("/api/risk/execution-outcomes", json=evidence)
    assert response.status_code == 422


def test_command_evidence_rejects_inline_secrets():
    evidence = _evidence().model_dump(mode="json")
    evidence["commands"] = [
        {
            "command_id": "cmd-secret",
            "command": "deploy --token=never-store-this",
            "exit_code": 0,
        }
    ]
    response = client.post("/api/risk/execution-outcomes", json=evidence)
    assert response.status_code == 422
    assert "never-store-this" not in response.text


def test_api_enforces_auth_and_project_consistency(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    payload = _evidence().model_dump(mode="json")
    denied = client.post("/api/risk/execution-outcomes", json=payload)
    assert denied.status_code == 401

    payload["project_id"] = "beta"
    mismatch = client.post(
        "/api/risk/execution-outcomes",
        headers={AUTH_HEADER: API_KEY},
        json=payload,
    )
    assert mismatch.status_code == 403
