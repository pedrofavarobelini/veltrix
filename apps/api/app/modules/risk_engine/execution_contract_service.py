from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from app.modules.caller_identity.schemas import AuthenticatedCallerContext
from app.modules.risk_engine.execution_contract_schemas import (
    ContractValidation,
    ContractValidationRequest,
    ExecutionContract,
    HumanOverrideRequest,
    HumanReviewDecision,
    HumanReviewRecord,
    RiskGate,
)
from app.modules.risk_engine.pre_execution_schemas import RiskDimensionName
from app.modules.risk_engine.pre_execution_service import pre_execution_risk_service
from app.modules.risk_engine.schemas import OperationKind, RiskRequest

FLAG_CONTRACT_SIGNING_KEY = "PEDROCORE_RISK_CONTRACT_SIGNING_KEY"
FLAG_REVIEWER_IDS = "PEDROCORE_RISK_REVIEWER_IDS"
CONTRACT_TTL_MINUTES = 15


class ContractConfigurationError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    normalized = to_jsonable_python(value)
    return json.dumps(
        normalized,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _signing_key() -> bytes:
    value = (os.environ.get(FLAG_CONTRACT_SIGNING_KEY) or "").strip()
    if len(value) < 32:
        raise ContractConfigurationError(
            f"{FLAG_CONTRACT_SIGNING_KEY} deve possuir pelo menos 32 caracteres."
        )
    return value.encode()


def _hmac(value: object) -> str:
    return "hmac-sha256:" + hmac.new(_signing_key(), _canonical(value), hashlib.sha256).hexdigest()


def _context_signature(request: RiskRequest) -> str:
    return "sha256:" + hashlib.sha256(_canonical(request)).hexdigest()


def _permission_required(operation: OperationKind) -> str | None:
    return {
        OperationKind.READ: "read:",
        OperationKind.WRITE: "write:",
        OperationKind.DELETE: "delete:",
        OperationKind.MIGRATE: "migrate:",
        OperationKind.DEPLOY: "deploy:",
        OperationKind.CONFIGURE: "configure:",
        OperationKind.EXECUTE: "execute:",
        OperationKind.UNKNOWN: None,
    }[operation]


class ExecutionContractService:
    @staticmethod
    def reviewer_authorized(caller: AuthenticatedCallerContext) -> bool:
        configured = {
            item.strip()
            for item in (os.environ.get(FLAG_REVIEWER_IDS) or "").split(",")
            if item.strip()
        }
        return caller.credential_id in configured and caller.identity_is_project_bound

    @staticmethod
    def _gate(analysis, request: RiskRequest) -> tuple[RiskGate, list[str]]:
        reasons: set[str] = set()
        scope = analysis.foundation.scope
        if scope.forbidden_targets:
            reasons.add("FORBIDDEN_SCOPE")
        required_permission = _permission_required(request.requested_operation.kind)
        permission_ok = required_permission is not None and any(
            item.lower().startswith(required_permission) for item in request.permissions
        )
        if not permission_ok:
            reasons.add("PERMISSION_CONFLICT")
        if request.requested_operation.kind is OperationKind.UNKNOWN:
            reasons.add("OPERATION_UNKNOWN")
        rule_codes = {item.reason_code for item in analysis.deterministic_rules}
        if "SECRETS_OR_ENV" in rule_codes and request.environment.lower() in {
            "prod",
            "production",
        }:
            reasons.add("PRODUCTION_SECRET_CHANGE")
        if reasons & {
            "FORBIDDEN_SCOPE",
            "PERMISSION_CONFLICT",
            "OPERATION_UNKNOWN",
            "PRODUCTION_SECRET_CHANGE",
        }:
            return RiskGate.BLOCK, sorted(reasons)

        if analysis.foundation.resolved_context.missing_context:
            reasons.add("CRITICAL_CONTEXT_MISSING")
        if any(item.severity.value in {"HIGH", "CRITICAL"} for item in analysis.signals):
            reasons.add("HIGH_RISK_REVIEW")
        if any(
            item.pattern_type.value in {"ANTI_PATTERN", "RISK_PATTERN", "FAILURE_PATTERN"}
            and item.confidence >= 0.7
            for item in analysis.historical_evidence.items
        ):
            reasons.add("HISTORICAL_RISK_REVIEW")
        if reasons:
            return RiskGate.REVIEW_REQUIRED, sorted(reasons)
        if analysis.signals or analysis.historical_evidence.sample_size:
            return RiskGate.PASS_WITH_WARNINGS, ["NON_BLOCKING_RISK_SIGNALS"]
        return RiskGate.PASS, ["POLICY_REQUIREMENTS_SATISFIED"]

    def issue(
        self,
        request: RiskRequest,
        *,
        now: datetime | None = None,
    ) -> ExecutionContract:
        _signing_key()
        analysis = pre_execution_risk_service.analyze(request)
        gate, reasons = self._gate(analysis, request)
        current = now or datetime.now(timezone.utc)
        dimensions = {item.dimension.value: item.score for item in analysis.risk_dimensions}
        required_backup = (
            dimensions[RiskDimensionName.DATA.value] >= 0.8
            or dimensions[RiskDimensionName.MIGRATION.value] >= 0.8
        )
        allowed_scope = sorted(set(analysis.foundation.scope.targets_in_scope))
        forbidden_scope = sorted(set(request.context.forbidden_scope))
        forbidden_operations = ["scope_expansion", "unsigned_override"]
        if gate is RiskGate.BLOCK:
            forbidden_operations.append(request.requested_operation.kind.value)
        risk_controls = sorted(
            {
                "verify_context_signature",
                "verify_contract_integrity",
                "enforce_allowed_scope",
                *({"create_backup"} if required_backup else set()),
                *({"human_review"} if gate in {RiskGate.REVIEW_REQUIRED, RiskGate.BLOCK} else set()),
            }
        )
        unsigned = {
            "contract_id": f"contract_{uuid.uuid4().hex}",
            "policy_version": "execution-contract-v1",
            "risk_policy_version": analysis.policy_version,
            "analysis_id": analysis.analysis_id,
            "project_id": request.project_id.strip().lower(),
            "environment": request.environment.strip().lower(),
            "agent_id": request.agent_id,
            "context_signature": _context_signature(request),
            "gate": gate,
            "allowed_scope": allowed_scope,
            "forbidden_scope": forbidden_scope,
            "allowed_files": sorted(item for item in allowed_scope if item.startswith("file:")),
            "forbidden_files": sorted(
                item for item in forbidden_scope if item.startswith("file:")
            ),
            "allowed_commands": (
                sorted(set(request.requested_operation.commands))
                if gate is not RiskGate.BLOCK
                else []
            ),
            "forbidden_operations": sorted(set(forbidden_operations)),
            "required_tests": sorted(set(request.context.required_tests)),
            "required_backup": required_backup,
            "required_review": gate in {RiskGate.REVIEW_REQUIRED, RiskGate.BLOCK},
            "risk_controls": risk_controls,
            "risk_dimensions": dimensions,
            "evidence_ids": sorted(item.evidence_id for item in analysis.evidence),
            "reason_codes": reasons,
            "created_at": current,
            "expires_at": current + timedelta(minutes=CONTRACT_TTL_MINUTES),
        }
        return ExecutionContract(**unsigned, integrity_signature=_hmac(unsigned))

    @staticmethod
    def _integrity_valid(contract: ExecutionContract) -> bool:
        unsigned = contract.model_dump(mode="json", exclude={"integrity_signature"})
        expected = _hmac(unsigned)
        return hmac.compare_digest(expected, contract.integrity_signature)

    def validate(
        self,
        payload: ContractValidationRequest,
        *,
        now: datetime | None = None,
    ) -> ContractValidation:
        contract = payload.contract
        reference = now or datetime.now(timezone.utc)
        integrity_valid = self._integrity_valid(contract)
        context_valid = (
            payload.current_request.project_id.strip().lower() == contract.project_id
            and _context_signature(payload.current_request) == contract.context_signature
        )
        expired = contract.expires_at <= reference
        reasons: list[str] = []
        if not integrity_valid:
            reasons.append("CONTRACT_INTEGRITY_INVALID")
        if not context_valid:
            reasons.append("CONTEXT_CHANGED")
        if expired:
            reasons.append("CONTRACT_EXPIRED")
        valid = not reasons and contract.gate in {
            RiskGate.PASS,
            RiskGate.PASS_WITH_WARNINGS,
        }
        if contract.gate is RiskGate.REVIEW_REQUIRED:
            reasons.append("HUMAN_REVIEW_REQUIRED")
        elif contract.gate is RiskGate.BLOCK:
            reasons.append("CONTRACT_BLOCKED")
        return ContractValidation(
            contract_id=contract.contract_id,
            valid=valid,
            gate=contract.gate,
            reason_codes=reasons,
            integrity_valid=integrity_valid,
            context_valid=context_valid,
            expired=expired,
        )

    def override(
        self,
        payload: HumanOverrideRequest,
        caller: AuthenticatedCallerContext,
        *,
        now: datetime | None = None,
    ) -> HumanReviewRecord:
        if not self.reviewer_authorized(caller):
            raise PermissionError("reviewer não autorizado")
        validation = self.validate(payload, now=now)
        current = now or datetime.now(timezone.utc)
        original = payload.contract.gate
        reasons = list(validation.reason_codes)
        if not validation.integrity_valid or not validation.context_valid or validation.expired:
            resulting = RiskGate.BLOCK
            reasons.append("INVALID_CONTRACT_CANNOT_BE_OVERRIDDEN")
        elif original is RiskGate.BLOCK:
            resulting = RiskGate.BLOCK
            reasons.append("BLOCK_OVERRIDE_FORBIDDEN")
        elif payload.decision is HumanReviewDecision.REJECT:
            resulting = RiskGate.BLOCK
            reasons.append("HUMAN_REJECTED")
        elif original is RiskGate.REVIEW_REQUIRED and payload.decision is HumanReviewDecision.APPROVE:
            resulting = RiskGate.PASS_WITH_WARNINGS
            reasons.append("HUMAN_APPROVAL_RECORDED")
        else:
            resulting = original
            reasons.append("HUMAN_ACKNOWLEDGEMENT_RECORDED")
        unsigned = {
            "review_id": f"review_{uuid.uuid4().hex}",
            "reviewer": caller.credential_id,
            "decision": payload.decision,
            "reason": payload.reason.strip(),
            "timestamp": current,
            "policy_version": "execution-contract-v1",
            "contract_id": payload.contract.contract_id,
            "original_gate": original,
            "resulting_gate": resulting,
            "reason_codes": sorted(set(reasons)),
        }
        return HumanReviewRecord(**unsigned, integrity_signature=_hmac(unsigned))

    @staticmethod
    def review_integrity_valid(record: HumanReviewRecord) -> bool:
        unsigned = record.model_dump(mode="json", exclude={"integrity_signature"})
        return hmac.compare_digest(_hmac(unsigned), record.integrity_signature)


execution_contract_service = ExecutionContractService()
