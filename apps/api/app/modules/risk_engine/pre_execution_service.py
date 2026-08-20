from __future__ import annotations

from collections import defaultdict

from app.modules.retrieval.schemas import RetrievalQuery
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_engine.pre_execution_schemas import (
    BlastRadius,
    HistoricalEvidence,
    HistoricalMemoryEvidence,
    PreExecutionRiskAnalysis,
    RiskDimension,
    RiskDimensionName,
    RiskEvidence,
    ScenarioSimulation,
    SemanticRiskAnalysis,
)
from app.modules.risk_engine.rules import evaluate_deterministic_rules
from app.modules.risk_engine.schemas import (
    OperationKind,
    RiskFinding,
    RiskRequest,
    RiskSeverity,
    RiskSignal,
)
from app.modules.risk_engine.service import _stable_id, risk_engine_foundation_service

_SEVERITY_SCORE = {
    RiskSeverity.INFO: 0.0,
    RiskSeverity.LOW: 0.2,
    RiskSeverity.MEDIUM: 0.5,
    RiskSeverity.HIGH: 0.8,
    RiskSeverity.CRITICAL: 1.0,
}


def _severity(score: float) -> RiskSeverity:
    if score >= 0.9:
        return RiskSeverity.CRITICAL
    if score >= 0.7:
        return RiskSeverity.HIGH
    if score >= 0.4:
        return RiskSeverity.MEDIUM
    if score > 0:
        return RiskSeverity.LOW
    return RiskSeverity.INFO


class PreExecutionRiskService:
    """Hybrid risk analysis: deterministic foundation + bounded memory evidence."""

    @staticmethod
    def _keywords(request: RiskRequest) -> list[str]:
        values = [request.requested_operation.kind.value.lower()]
        values.extend(request.requested_operation.targets)
        return [value[:64] for value in values[:12]]

    def _history(self, request: RiskRequest, analysis_id: str) -> HistoricalEvidence:
        result = retrieval_service.retrieve(
            RetrievalQuery(
                query_id=f"{analysis_id}-history",
                producer=request.producer,
                project_id=request.project_id,
                keywords=self._keywords(request),
                include_anti_patterns=True,
                max_results=5,
                max_context_chars=2000,
                min_evidence_count=1,
            )
        )
        return HistoricalEvidence(
            retrieval_policy_version=result.policy_version,
            status=result.status,
            sample_size=len(result.items),
            items=[
                HistoricalMemoryEvidence(
                    memory_id=item.memory_id,
                    pattern_type=item.pattern_type,
                    lifecycle=item.lifecycle,
                    confidence=item.confidence,
                    relevance_score=item.relevance_score,
                    policy_version=item.policy_version,
                )
                for item in result.items
            ],
        )

    @staticmethod
    def _dimensions(rules, foundation) -> list[RiskDimension]:
        reasons: dict[RiskDimensionName, list[str]] = defaultdict(list)
        mapping = {
            "scope": (RiskDimensionName.SCOPE, RiskDimensionName.REGRESSION),
            "data": (RiskDimensionName.DATA,),
            "security": (RiskDimensionName.SECURITY,),
            "migration": (RiskDimensionName.MIGRATION, RiskDimensionName.DATA),
            "operational": (RiskDimensionName.OPERATIONAL, RiskDimensionName.REGRESSION),
        }
        score_by_reason: dict[tuple[RiskDimensionName, str], float] = {}
        for rule in rules:
            for dimension in mapping[rule.category]:
                reasons[dimension].append(rule.reason_code)
                score_by_reason[(dimension, rule.reason_code)] = _SEVERITY_SCORE[rule.severity]
        for signal in foundation.signals:
            dimension = (
                RiskDimensionName.SCOPE
                if signal.category == "scope"
                else RiskDimensionName.OPERATIONAL
            )
            reasons[dimension].append(signal.code)
            score_by_reason[(dimension, signal.code)] = _SEVERITY_SCORE[signal.severity]
        result: list[RiskDimension] = []
        for dimension in RiskDimensionName:
            dimension_reasons = sorted(set(reasons[dimension]))
            score = max(
                (score_by_reason[(dimension, reason)] for reason in dimension_reasons),
                default=0.0,
            )
            result.append(
                RiskDimension(
                    dimension=dimension,
                    score=score,
                    severity=_severity(score),
                    reason_codes=dimension_reasons,
                )
            )
        return result

    @staticmethod
    def _blast_radius(request: RiskRequest, rules) -> BlastRadius:
        targets = request.requested_operation.targets
        files = sorted(item for item in targets if item.startswith("file:"))
        modules = sorted(item for item in targets if item.startswith("module:"))
        database_rules = {"DATABASE_MIGRATION", "SCHEMA_CHANGE", "DELETE_OPERATION"}
        database = (
            [request.context.database]
            if request.context.database
            and any(rule.reason_code in database_rules for rule in rules)
            else []
        )
        users = [request.context.user_scope] if request.context.user_scope else []
        security = sorted(
            rule.reason_code for rule in rules if rule.category == "security"
        )
        severity = max(
            (rule.severity for rule in rules),
            key=lambda value: _SEVERITY_SCORE[value],
            default=RiskSeverity.INFO,
        )
        if len(targets) >= 20 and _SEVERITY_SCORE[severity] < 0.8:
            severity = RiskSeverity.HIGH
        return BlastRadius(
            files=files,
            modules=modules,
            database=[item for item in database if item],
            users=users,
            permissions=sorted(set(request.permissions)),
            environments=[request.environment.lower()],
            external_integrations=sorted(set(request.context.external_integrations)),
            security_boundaries=security,
            magnitude=severity,
        )

    @staticmethod
    def _simulations(request: RiskRequest, rules, foundation) -> list[ScenarioSimulation]:
        codes = sorted({rule.reason_code for rule in rules})
        forbidden = [item.code for item in foundation.signals if item.category == "scope"]
        destructive = request.requested_operation.destructive or request.requested_operation.kind is OperationKind.DELETE
        return [
            ScenarioSimulation(scenario="success", severity=RiskSeverity.INFO, trigger_codes=[], expected_effect="Mudanças permanecem no escopo e validações são concluídas."),
            ScenarioSimulation(scenario="partial_failure", severity=RiskSeverity.HIGH if destructive else RiskSeverity.MEDIUM, trigger_codes=codes, expected_effect="Parte da operação falha e exige contenção sem ampliar escopo."),
            ScenarioSimulation(scenario="scope_deviation", severity=RiskSeverity.CRITICAL if forbidden else RiskSeverity.HIGH, trigger_codes=forbidden, expected_effect="Alvos fora do contrato precisam ser bloqueados antes da execução."),
            ScenarioSimulation(scenario="dependency_failure", severity=RiskSeverity.MEDIUM, trigger_codes=["DEPENDENCY_FAILURE"], expected_effect="Dependência indisponível impede conclusão segura."),
            ScenarioSimulation(scenario="rollback_requirement", severity=RiskSeverity.HIGH if not request.context.rollback_plan_present and foundation.intent.mutating else RiskSeverity.MEDIUM, trigger_codes=["ROLLBACK_REQUIRED"], expected_effect="Restauração deve ocorrer usando plano previamente aprovado."),
            ScenarioSimulation(scenario="security_impact", severity=max((rule.severity for rule in rules if rule.category == "security"), key=lambda value: _SEVERITY_SCORE[value], default=RiskSeverity.LOW), trigger_codes=sorted(rule.reason_code for rule in rules if rule.category == "security"), expected_effect="Boundary de segurança afetado exige revisão explícita."),
        ]

    def analyze(self, request: RiskRequest) -> PreExecutionRiskAnalysis:
        foundation = risk_engine_foundation_service.analyze(request)
        rules = evaluate_deterministic_rules(request)
        analysis_id = _stable_id("analysis", foundation.assessment_id, [rule.rule_id for rule in rules])
        history = self._history(request, analysis_id)
        signals = list(foundation.signals)
        evidence: list[RiskEvidence] = []
        for rule in rules:
            signal = RiskSignal(
                signal_id=_stable_id("sig", analysis_id, rule.rule_id),
                code=rule.reason_code,
                category=rule.category,
                severity=rule.severity,
                detail=f"Regra determinística acionada: {rule.rule_id}.",
            )
            signals.append(signal)
            evidence.append(
                RiskEvidence(
                    evidence_id=_stable_id("ev", signal.signal_id),
                    source="deterministic_rule",
                    reference_id=rule.rule_id,
                    reason_code=rule.reason_code,
                )
            )
        for item in history.items:
            evidence.append(
                RiskEvidence(
                    evidence_id=_stable_id("ev", analysis_id, item.memory_id),
                    source="operational_memory",
                    reference_id=item.memory_id,
                    reason_code="HISTORICAL_PATTERN",
                )
            )
        findings = list(foundation.findings)
        existing_codes = {item.reason_code for item in findings}
        findings.extend(
            RiskFinding(
                finding_id=_stable_id("find", analysis_id, signal.code),
                signal_ids=[signal.signal_id],
                title=signal.detail,
                severity=signal.severity,
                reason_code=signal.code,
            )
            for signal in signals
            if signal.code not in existing_codes and signal.severity is not RiskSeverity.INFO
        )
        dimensions = self._dimensions(rules, foundation)
        semantic = SemanticRiskAnalysis(
            matched_concepts=sorted({rule.category for rule in rules}),
            signal_codes=sorted({rule.reason_code for rule in rules}),
        )
        confidence = round(
            min(1.0, foundation.confidence * 0.8 + (0.1 if rules else 0.0) + (0.1 if history.sample_size else 0.0)),
            6,
        )
        return PreExecutionRiskAnalysis(
            analysis_id=analysis_id,
            request_id=request.request_id,
            project_id=request.project_id.strip().lower(),
            foundation=foundation,
            signals=signals,
            findings=findings,
            evidence=evidence,
            deterministic_rules=rules,
            semantic_analysis=semantic,
            historical_evidence=history,
            blast_radius=self._blast_radius(request, rules),
            simulations=self._simulations(request, rules, foundation),
            risk_dimensions=dimensions,
            confidence=confidence,
            uncertainty=round(1.0 - confidence, 6),
        )


pre_execution_risk_service = PreExecutionRiskService()
