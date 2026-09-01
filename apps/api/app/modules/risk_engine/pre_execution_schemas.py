from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.operational_memory.schemas import MemoryLifecycle, PatternType
from app.modules.risk_engine.blast_radius_metric import BlastRadiusMetric
from app.modules.risk_engine.schemas import RiskAssessment, RiskFinding, RiskSeverity, RiskSignal

PRE_EXECUTION_RISK_POLICY_VERSION = "pre-execution-risk-v1"


class RiskDimensionName(str, Enum):
    SCOPE = "scope_risk"
    DATA = "data_risk"
    SECURITY = "security_risk"
    MIGRATION = "migration_risk"
    REGRESSION = "regression_risk"
    OPERATIONAL = "operational_risk"


class RiskEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source: str
    reference_id: str
    reason_code: str


class DeterministicRuleMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    rule_version: str
    category: str
    severity: RiskSeverity
    reason_code: str


class SemanticRiskAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analyzer_version: Literal["semantic-catalog-v1"] = "semantic-catalog-v1"
    matched_concepts: list[str] = Field(default_factory=list)
    signal_codes: list[str] = Field(default_factory=list)
    provider_called: Literal[False] = False


class HistoricalMemoryEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str
    pattern_type: PatternType
    lifecycle: MemoryLifecycle
    confidence: float = Field(..., ge=0.0, le=1.0)
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    policy_version: str


class HistoricalEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["operational_memory"] = "operational_memory"
    retrieval_policy_version: str
    status: str
    sample_size: int = Field(..., ge=0)
    items: list[HistoricalMemoryEvidence] = Field(default_factory=list)


class BlastRadius(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    database: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    environments: list[str] = Field(default_factory=list)
    external_integrations: list[str] = Field(default_factory=list)
    security_boundaries: list[str] = Field(default_factory=list)
    magnitude: RiskSeverity
    # Stage R3: metrica quantitativa de ALCANCE, aditiva e opcional.
    # `magnitude` (severidade) e preservada; as duas respondem perguntas
    # diferentes e por isso coexistem em vez de uma substituir a outra.
    # `None` em analises produzidas antes do R3.
    metric: BlastRadiusMetric | None = None


class ScenarioSimulation(BaseModel):
    """Cenario analitico. NUNCA executa a operacao alvo.

    Stage R5: os campos abaixo de `expected_effect` sao ADITIVOS e opcionais.
    Eles existem porque "este cenario e HIGH" nao ajuda ninguem a agir — o que
    ajuda e saber o que dispara, o que ele atinge, como conter, o que verificar
    e o que sobra de risco depois da contencao.

    `confidence` e explicito porque um cenario derivado de regra deterministica
    e mais confiavel que um derivado de heuristica, e apresentar os dois com o
    mesmo peso seria esconder a diferenca.
    """

    model_config = ConfigDict(extra="forbid")

    scenario: str
    mode: Literal["analytical_dry_run"] = "analytical_dry_run"
    severity: RiskSeverity
    trigger_codes: list[str] = Field(default_factory=list)
    expected_effect: str

    # Stage R5 — aditivos. `None`/vazio em analises anteriores.
    preconditions: list[str] = Field(default_factory=list)
    affected_scope: list[str] = Field(default_factory=list)
    containment: str | None = None
    rollback_requirement: Literal["none", "recommended", "required"] = "none"
    verification: list[str] = Field(default_factory=list)
    residual_risk: RiskSeverity | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    target_operation_executed: Literal[False] = False


class RiskDimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: RiskDimensionName
    score: float = Field(..., ge=0.0, le=1.0)
    severity: RiskSeverity
    reason_codes: list[str] = Field(default_factory=list)


class PreExecutionRiskAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str
    request_id: str
    project_id: str
    policy_version: Literal["pre-execution-risk-v1"] = PRE_EXECUTION_RISK_POLICY_VERSION
    foundation: RiskAssessment
    signals: list[RiskSignal] = Field(default_factory=list)
    findings: list[RiskFinding] = Field(default_factory=list)
    evidence: list[RiskEvidence] = Field(default_factory=list)
    deterministic_rules: list[DeterministicRuleMatch] = Field(default_factory=list)
    semantic_analysis: SemanticRiskAnalysis
    historical_evidence: HistoricalEvidence
    blast_radius: BlastRadius
    simulations: list[ScenarioSimulation]
    risk_dimensions: list[RiskDimension]
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty: float = Field(..., ge=0.0, le=1.0)
    target_operation_executed: Literal[False] = False
    provider_called: Literal[False] = False
    operational_memory_created: Literal[False] = False
