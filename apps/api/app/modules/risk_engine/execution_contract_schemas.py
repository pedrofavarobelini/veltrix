from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.risk_engine.schemas import RiskRequest

EXECUTION_CONTRACT_POLICY_VERSION = "execution-contract-v1"


class RiskGate(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


class ExecutionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str
    policy_version: Literal["execution-contract-v1"] = EXECUTION_CONTRACT_POLICY_VERSION
    risk_policy_version: str
    analysis_id: str
    project_id: str
    environment: str
    agent_id: str
    context_signature: str = Field(..., pattern=r"^sha256:[a-f0-9]{64}$")
    gate: RiskGate
    allowed_scope: list[str] = Field(default_factory=list)
    forbidden_scope: list[str] = Field(default_factory=list)
    allowed_files: list[str] = Field(default_factory=list)
    forbidden_files: list[str] = Field(default_factory=list)
    allowed_commands: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    required_backup: bool = False
    required_review: bool = False
    risk_controls: list[str] = Field(default_factory=list)
    risk_dimensions: dict[str, float] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    created_at: datetime
    expires_at: datetime
    integrity_signature: str = Field(..., pattern=r"^hmac-sha256:[a-f0-9]{64}$")


class ContractIssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    contract: ExecutionContract


class ContractValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    producer: str = Field(..., min_length=3, max_length=64)
    contract: ExecutionContract
    current_request: RiskRequest


class ContractValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_id: str
    valid: bool
    gate: RiskGate
    reason_codes: list[str] = Field(default_factory=list)
    integrity_valid: bool
    context_valid: bool
    expired: bool


class HumanReviewDecision(str, Enum):
    APPROVE = "APPROVE"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    REJECT = "REJECT"


class HumanOverrideRequest(ContractValidationRequest):
    decision: HumanReviewDecision
    reason: str = Field(..., min_length=10, max_length=500)


class HumanReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    review_id: str
    reviewer: str
    decision: HumanReviewDecision
    reason: str
    timestamp: datetime
    policy_version: Literal["execution-contract-v1"] = EXECUTION_CONTRACT_POLICY_VERSION
    contract_id: str
    original_gate: RiskGate
    resulting_gate: RiskGate
    reason_codes: list[str] = Field(default_factory=list)
    integrity_signature: str = Field(..., pattern=r"^hmac-sha256:[a-f0-9]{64}$")
