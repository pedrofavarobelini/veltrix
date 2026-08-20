"""Gate 9 — signed execution contracts, fail-closed gates and human review."""

import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.caller_identity.service import FLAG_CALLER_REGISTRY
from app.modules.retrieval.schemas import RetrievalResponse
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_engine.execution_contract_schemas import (
    ContractValidationRequest,
    HumanReviewRecord,
    RiskGate,
)
from app.modules.risk_engine.execution_contract_service import (
    FLAG_CONTRACT_SIGNING_KEY,
    FLAG_REVIEWER_IDS,
    execution_contract_service,
)
from app.modules.risk_engine.schemas import RiskRequest

client = TestClient(app)
AUTH_HEADER = "X-PedroCore-Api-Key"
ALPHA_KEY = "risk-contract-alpha-key-synthetic"
BETA_KEY = "risk-contract-beta-key-synthetic"
SIGNING_KEY = "synthetic-contract-signing-key-with-more-than-32-characters"


def _payload(**overrides) -> dict:
    values = {
        "request_id": "contract-request-001",
        "producer": "alpha-technical-tool",
        "project_id": "alpha",
        "request_text": "Change the billing module within approved scope.",
        "environment": "development",
        "agent_id": "codex-local",
        "permissions": ["read:billing", "write:billing"],
        "context": {
            "allowed_scope": ["module:billing", "file:billing/service.py"],
            "forbidden_scope": ["module:auth", "file:auth/service.py"],
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
        },
    }
    values.update(overrides)
    return values


def _request(**overrides) -> RiskRequest:
    return RiskRequest.model_validate(_payload(**overrides))


def _empty_retrieval(query) -> RetrievalResponse:
    return RetrievalResponse(query_id=query.query_id, project_id=query.project_id)


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


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv(FLAG_CONTRACT_SIGNING_KEY, SIGNING_KEY)
    monkeypatch.delenv(FLAG_REVIEWER_IDS, raising=False)
    monkeypatch.delenv(FLAG_CALLER_REGISTRY, raising=False)
    monkeypatch.setattr(retrieval_service, "retrieve", _empty_retrieval)


def test_pass_contract_is_signed_bounded_and_valid():
    request = _request()
    contract = execution_contract_service.issue(request)
    validation = execution_contract_service.validate(
        ContractValidationRequest(
            producer=request.producer,
            contract=contract,
            current_request=request,
        )
    )
    assert contract.gate is RiskGate.PASS
    assert contract.allowed_scope == ["file:billing/service.py", "module:billing"]
    assert contract.forbidden_scope == ["file:auth/service.py", "module:auth"]
    assert contract.allowed_commands == []
    assert contract.required_tests == ["billing unit"]
    assert contract.integrity_signature.startswith("hmac-sha256:")
    assert validation.valid is True
    assert validation.integrity_valid is True


def test_pass_with_warnings_is_not_silently_promoted():
    request = _request(
        request_text="Read billing.",
        permissions=["read:billing"],
        context={
            "allowed_scope": ["module:billing"],
            "forbidden_scope": [],
        },
        requested_operation={"kind": "READ", "targets": ["module:billing"]},
    )
    contract = execution_contract_service.issue(request)
    assert contract.gate is RiskGate.PASS_WITH_WARNINGS
    assert contract.reason_codes == ["NON_BLOCKING_RISK_SIGNALS"]


def test_high_risk_requires_review_and_gate_validation_remains_false():
    request = _request(request_text="Edit the CI/CD workflow pipeline.")
    contract = execution_contract_service.issue(request)
    validation = execution_contract_service.validate(
        ContractValidationRequest(
            producer=request.producer,
            contract=contract,
            current_request=request,
        )
    )
    assert contract.gate is RiskGate.REVIEW_REQUIRED
    assert contract.required_review is True
    assert validation.valid is False
    assert "HUMAN_REVIEW_REQUIRED" in validation.reason_codes


def test_forbidden_scope_and_permission_conflict_block():
    forbidden = execution_contract_service.issue(
        _request(
            requested_operation={
                "kind": "WRITE",
                "targets": ["module:auth"],
            }
        )
    )
    permission = execution_contract_service.issue(
        _request(permissions=["read:billing"])
    )
    assert forbidden.gate is RiskGate.BLOCK
    assert "FORBIDDEN_SCOPE" in forbidden.reason_codes
    assert permission.gate is RiskGate.BLOCK
    assert "PERMISSION_CONFLICT" in permission.reason_codes


def test_missing_context_fails_closed_to_review():
    contract = execution_contract_service.issue(
        _request(
            request_text="Read billing.",
            permissions=["read:billing"],
            context={"allowed_scope": [], "forbidden_scope": []},
            requested_operation={"kind": "READ", "targets": ["module:billing"]},
        )
    )
    assert contract.gate is RiskGate.REVIEW_REQUIRED
    assert "CRITICAL_CONTEXT_MISSING" in contract.reason_codes


def test_expired_manipulated_and_changed_context_are_invalid():
    request = _request()
    contract = execution_contract_service.issue(request)
    payload = ContractValidationRequest(
        producer=request.producer,
        contract=contract,
        current_request=request,
    )
    expired = execution_contract_service.validate(
        payload,
        now=contract.expires_at + timedelta(seconds=1),
    )
    tampered_contract = contract.model_copy(update={"allowed_scope": ["module:auth"]})
    tampered = execution_contract_service.validate(
        payload.model_copy(update={"contract": tampered_contract})
    )
    changed_request = _request(request_text="Different request context.")
    changed = execution_contract_service.validate(
        payload.model_copy(update={"current_request": changed_request})
    )
    assert expired.valid is False and expired.expired is True
    assert tampered.valid is False and tampered.integrity_valid is False
    assert changed.valid is False and changed.context_valid is False


def test_issue_api_rejects_mass_assignment_and_missing_signing_key(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    forged = {**_payload(), "gate": "PASS", "integrity_signature": "forged"}
    rejected = client.post(
        "/api/risk/contracts",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=forged,
    )
    assert rejected.status_code == 422

    monkeypatch.delenv(FLAG_CONTRACT_SIGNING_KEY)
    unavailable = client.post(
        "/api/risk/contracts",
        headers={AUTH_HEADER: ALPHA_KEY},
        json=_payload(),
    )
    assert unavailable.status_code == 503
    assert unavailable.json()["error_code"] == "RISK_CONTRACT_CONFIGURATION_INVALID"


def test_forged_project_cannot_validate_another_projects_contract(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    contract = execution_contract_service.issue(_request())
    response = client.post(
        "/api/risk/contracts/validate",
        headers={AUTH_HEADER: BETA_KEY},
        json={
            "producer": "beta-technical-tool",
            "contract": contract.model_dump(mode="json"),
            "current_request": _payload(producer="beta-technical-tool", project_id="beta"),
        },
    )
    assert response.status_code == 403


def test_unauthorized_override_is_rejected(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    request = _request(request_text="Edit CI/CD workflow pipeline.")
    contract = execution_contract_service.issue(request)
    response = client.post(
        "/api/risk/contracts/override",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={
            "producer": request.producer,
            "contract": contract.model_dump(mode="json"),
            "current_request": request.model_dump(mode="json"),
            "decision": "APPROVE",
            "reason": "Reviewed synthetic CI controls and evidence.",
        },
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "RISK_OVERRIDE_NOT_AUTHORIZED"


def test_authorized_review_is_signed_traceable_and_never_silent(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    monkeypatch.setenv(FLAG_REVIEWER_IDS, "alpha-technical-tool")
    request = _request(request_text="Edit CI/CD workflow pipeline.")
    contract = execution_contract_service.issue(request)
    response = client.post(
        "/api/risk/contracts/override",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={
            "producer": request.producer,
            "contract": contract.model_dump(mode="json"),
            "current_request": request.model_dump(mode="json"),
            "decision": "APPROVE",
            "reason": "Reviewed synthetic CI controls and evidence.",
        },
    )
    assert response.status_code == 200
    review = response.json()
    assert review["reviewer"] == "alpha-technical-tool"
    assert review["original_gate"] == "REVIEW_REQUIRED"
    assert review["resulting_gate"] == "PASS_WITH_WARNINGS"
    assert review["integrity_signature"].startswith("hmac-sha256:")
    assert "HUMAN_APPROVAL_RECORDED" in review["reason_codes"]
    record = HumanReviewRecord.model_validate(review)
    assert execution_contract_service.review_integrity_valid(record) is True
    manipulated = record.model_copy(update={"resulting_gate": RiskGate.PASS})
    assert execution_contract_service.review_integrity_valid(manipulated) is False


def test_even_authorized_reviewer_cannot_override_block(monkeypatch):
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, _registry())
    monkeypatch.setenv(FLAG_REVIEWER_IDS, "alpha-technical-tool")
    request = _request(permissions=["read:billing"])
    contract = execution_contract_service.issue(request)
    response = client.post(
        "/api/risk/contracts/override",
        headers={AUTH_HEADER: ALPHA_KEY},
        json={
            "producer": request.producer,
            "contract": contract.model_dump(mode="json"),
            "current_request": request.model_dump(mode="json"),
            "decision": "APPROVE",
            "reason": "Attempted override remains blocked by policy.",
        },
    )
    assert response.status_code == 200
    assert response.json()["resulting_gate"] == "BLOCK"
    assert "BLOCK_OVERRIDE_FORBIDDEN" in response.json()["reason_codes"]
