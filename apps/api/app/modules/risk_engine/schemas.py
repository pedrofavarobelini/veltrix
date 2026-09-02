from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RISK_SCHEMA_VERSION = "1.0"
RISK_FOUNDATION_POLICY_VERSION = "risk-foundation-v1"


class OperationKind(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    MIGRATE = "MIGRATE"
    DEPLOY = "DEPLOY"
    CONFIGURE = "CONFIGURE"
    EXECUTE = "EXECUTE"
    UNKNOWN = "UNKNOWN"


class RiskSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RequestedOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: OperationKind
    targets: list[str] = Field(default_factory=list, max_length=100)
    expected_changes: list[str] = Field(default_factory=list, max_length=100)
    commands: list[str] = Field(default_factory=list, max_length=50)
    destructive: bool = False
    external_effects: bool = False

    @field_validator("commands")
    @classmethod
    def _commands_must_not_contain_inline_secrets(cls, values: list[str]) -> list[str]:
        forbidden = ("api_key=", "apikey=", "token=", "password=", "secret=")
        if any(any(marker in value.lower() for marker in forbidden) for value in values):
            raise ValueError("commands não podem transportar secrets inline")
        return values


class RiskContextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed_scope: list[str] = Field(default_factory=list, max_length=100)
    forbidden_scope: list[str] = Field(default_factory=list, max_length=100)
    known_files: list[str] = Field(default_factory=list, max_length=200)
    known_modules: list[str] = Field(default_factory=list, max_length=100)
    database: str | None = Field(default=None, max_length=128)
    user_scope: str | None = Field(default=None, max_length=128)
    external_integrations: list[str] = Field(default_factory=list, max_length=50)
    constraints: list[str] = Field(default_factory=list, max_length=100)
    acceptance_criteria: list[str] = Field(default_factory=list, max_length=100)
    required_tests: list[str] = Field(default_factory=list, max_length=100)
    rollback_plan_present: bool = False


class RiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = RISK_SCHEMA_VERSION
    request_id: str = Field(..., min_length=3, max_length=128)
    producer: str = Field(..., min_length=3, max_length=64)
    project_id: str = Field(..., min_length=1, max_length=128)
    request_text: str = Field(..., min_length=1, max_length=4000)
    environment: str = Field(..., min_length=1, max_length=32)
    agent_id: str = Field(..., min_length=1, max_length=128)
    permissions: list[str] = Field(default_factory=list, max_length=50)
    context: RiskContextInput
    requested_operation: RequestedOperation


class ExecutionIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: OperationKind
    inferred_operation: OperationKind
    targets: list[str] = Field(default_factory=list)
    mutating: bool
    destructive: bool
    external_effects: bool
    explicit_intent: bool
    intent_consistent: bool
    # Termos de operacao citados como PROIBIDOS no pedido. Aditivo e opcional.
    #
    # Existe para que a proibicao vire restricao VISIVEL em vez de sumir. Um
    # pedido que diz "nao altere migrations" precisa registrar que migrations
    # foi citado e que foi citado como proibido — sem que isso vire intencao,
    # alvo afetado ou cenario, que era exatamente o defeito anterior.
    forbidden_mentions: list[str] = Field(default_factory=list)


class ResolvedContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    environment: str
    agent_id: str
    permissions: list[str] = Field(default_factory=list)
    allowed_scope: list[str] = Field(default_factory=list)
    forbidden_scope: list[str] = Field(default_factory=list)
    known_files: list[str] = Field(default_factory=list)
    known_modules: list[str] = Field(default_factory=list)
    database: str | None = None
    user_scope: str | None = None
    external_integrations: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    rollback_plan_present: bool = False
    missing_context: list[str] = Field(default_factory=list)


class PromptQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(..., ge=0.0, le=1.0)
    has_explicit_operation: bool
    has_targets: bool
    has_constraints: bool
    has_acceptance_criteria: bool
    has_tests: bool
    has_rollback: bool
    reason_codes: list[str] = Field(default_factory=list)


class AmbiguityAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ambiguous: bool
    ambiguity_codes: list[str] = Field(default_factory=list)


class ScopeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bounded: bool
    targets_in_scope: list[str] = Field(default_factory=list)
    targets_outside_scope: list[str] = Field(default_factory=list)
    forbidden_targets: list[str] = Field(default_factory=list)
    unknown_targets: list[str] = Field(default_factory=list)


class RiskSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    code: str
    category: str
    severity: RiskSeverity
    detail: str
    deterministic: Literal[True] = True


class RiskFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str
    signal_ids: list[str]
    title: str
    severity: RiskSeverity
    reason_code: str


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = RISK_SCHEMA_VERSION
    assessment_id: str
    request_id: str
    project_id: str
    policy_version: Literal["risk-foundation-v1"] = RISK_FOUNDATION_POLICY_VERSION
    intent: ExecutionIntent
    resolved_context: ResolvedContext
    prompt_quality: PromptQuality
    ambiguity: AmbiguityAnalysis
    scope: ScopeAnalysis
    signals: list[RiskSignal] = Field(default_factory=list)
    findings: list[RiskFinding] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    target_operation_executed: Literal[False] = False
    provider_called: Literal[False] = False
    operational_memory_created: Literal[False] = False
