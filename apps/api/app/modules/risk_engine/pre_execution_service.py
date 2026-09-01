from __future__ import annotations

from collections import defaultdict

from app.modules.retrieval.schemas import RetrievalQuery
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_engine.persistence_service import risk_persistence_service
from app.modules.risk_engine.repository import RiskRepositoryError
from app.modules.risk_engine.blast_radius_metric import compute_blast_radius_metric
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
        radius = BlastRadius(
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
        # A metrica e derivada do proprio raio ja montado: uma fonte, nao duas.
        return radius.model_copy(
            update={"metric": compute_blast_radius_metric(radius)}
        )

    @staticmethod
    def _simulations(request: RiskRequest, rules, foundation) -> list[ScenarioSimulation]:
        """Cenarios analiticos relevantes. Stage R5.

        Os seis primeiros valem para qualquer operacao mutante e por isso sao
        sempre emitidos. Os demais so aparecem quando o FATO correspondente
        existe na requisicao — cenario irrelevante emitido para completar lista
        treina quem le a ignorar a lista inteira.

        Nada aqui executa: `mode` continua `analytical_dry_run` e
        `target_operation_executed` continua `False`.
        """
        codes = sorted({rule.reason_code for rule in rules})
        forbidden = [item.code for item in foundation.signals if item.category == "scope"]
        destructive = (
            request.requested_operation.destructive
            or request.requested_operation.kind is OperationKind.DELETE
        )
        targets = sorted(set(request.requested_operation.targets))
        security_codes = sorted(
            rule.reason_code for rule in rules if rule.category == "security"
        )
        security_severity = max(
            (rule.severity for rule in rules if rule.category == "security"),
            key=lambda value: _SEVERITY_SCORE[value],
            default=RiskSeverity.LOW,
        )
        mutating = foundation.intent.mutating
        no_rollback = not request.context.rollback_plan_present
        migration_codes = sorted(
            rule.reason_code
            for rule in rules
            if rule.reason_code in {"DATABASE_MIGRATION", "SCHEMA_CHANGE"}
        )
        required_tests = sorted(set(request.context.required_tests))
        integrations = sorted(set(request.context.external_integrations))
        database_scope = [request.context.database] if request.context.database else []

        scenarios = [
            ScenarioSimulation(
                scenario="success",
                severity=RiskSeverity.INFO,
                trigger_codes=[],
                expected_effect="Mudancas permanecem no escopo e validacoes sao concluidas.",
                preconditions=["escopo respeitado", "validacoes disponiveis"],
                affected_scope=targets,
                containment="Nenhuma contencao necessaria.",
                rollback_requirement="none",
                verification=required_tests or ["suite declarada pelo consumidor"],
                residual_risk=RiskSeverity.INFO,
                confidence=0.9,
            ),
            ScenarioSimulation(
                scenario="partial_failure",
                severity=RiskSeverity.HIGH if destructive else RiskSeverity.MEDIUM,
                trigger_codes=codes,
                expected_effect="Parte da operacao falha e exige contencao sem ampliar escopo.",
                preconditions=["operacao interrompida no meio"],
                affected_scope=targets,
                containment="Interromper e conter dentro do escopo aprovado.",
                rollback_requirement="required" if destructive else "recommended",
                verification=required_tests,
                residual_risk=RiskSeverity.MEDIUM if destructive else RiskSeverity.LOW,
                confidence=0.7 if codes else 0.5,
            ),
            ScenarioSimulation(
                scenario="scope_deviation",
                severity=RiskSeverity.CRITICAL if forbidden else RiskSeverity.HIGH,
                trigger_codes=forbidden,
                expected_effect="Alvos fora do contrato precisam ser bloqueados antes da execucao.",
                preconditions=["alvo fora do escopo declarado"],
                affected_scope=sorted(set(request.context.forbidden_scope)) or targets,
                containment="Bloquear antes da execucao; desvio nao e contido depois.",
                rollback_requirement="required" if forbidden else "recommended",
                verification=["conferencia de escopo contra o contrato"],
                residual_risk=RiskSeverity.HIGH if forbidden else RiskSeverity.MEDIUM,
                confidence=0.9 if forbidden else 0.6,
            ),
            ScenarioSimulation(
                scenario="dependency_failure",
                severity=RiskSeverity.MEDIUM,
                trigger_codes=["DEPENDENCY_FAILURE"],
                expected_effect="Dependencia indisponivel impede conclusao segura.",
                preconditions=["dependencia necessaria indisponivel"],
                affected_scope=targets,
                containment="Abortar antes de mutacao parcial.",
                rollback_requirement="recommended" if mutating else "none",
                verification=["disponibilidade da dependencia"],
                residual_risk=RiskSeverity.LOW,
                confidence=0.5,
            ),
            ScenarioSimulation(
                scenario="rollback_requirement",
                severity=RiskSeverity.HIGH if no_rollback and mutating else RiskSeverity.MEDIUM,
                trigger_codes=["ROLLBACK_REQUIRED"],
                expected_effect="Restauracao deve ocorrer usando plano previamente aprovado.",
                preconditions=(
                    ["plano de rollback ausente"]
                    if no_rollback
                    else ["plano de rollback declarado"]
                ),
                affected_scope=targets,
                containment=(
                    "Sem plano aprovado, a restauracao e improvisada."
                    if no_rollback
                    else "Executar o plano declarado."
                ),
                rollback_requirement="required" if mutating else "none",
                verification=["plano de rollback exercitado"],
                residual_risk=(
                    RiskSeverity.HIGH if no_rollback and mutating else RiskSeverity.LOW
                ),
                confidence=0.8,
            ),
            ScenarioSimulation(
                scenario="security_impact",
                severity=security_severity,
                trigger_codes=security_codes,
                expected_effect="Boundary de seguranca afetado exige revisao explicita.",
                preconditions=["fronteira de seguranca tocada"],
                affected_scope=security_codes or targets,
                containment="Revisao humana antes da execucao.",
                rollback_requirement="required" if security_codes else "recommended",
                verification=["revisao de seguranca registrada"],
                residual_risk=security_severity,
                confidence=0.85 if security_codes else 0.4,
            ),
        ]

        # --- condicionais: so quando o fato correspondente existe ------------

        if destructive or migration_codes:
            scenarios.append(
                ScenarioSimulation(
                    scenario="data_corruption",
                    severity=RiskSeverity.CRITICAL,
                    trigger_codes=migration_codes or ["DESTRUCTIVE_OPERATION"],
                    expected_effect="Dado corrompido ou perdido sem restauracao garantida.",
                    preconditions=["operacao destrutiva ou alteracao de schema"],
                    affected_scope=database_scope or targets,
                    containment="Backup verificado antes de iniciar.",
                    rollback_requirement="required",
                    verification=["restauracao testada a partir do backup"],
                    residual_risk=RiskSeverity.HIGH,
                    confidence=0.85,
                )
            )

        if migration_codes:
            scenarios.append(
                ScenarioSimulation(
                    scenario="migration_failure",
                    severity=RiskSeverity.HIGH,
                    trigger_codes=migration_codes,
                    expected_effect="Migracao falha no meio e deixa o schema inconsistente.",
                    preconditions=["migracao aplicada parcialmente"],
                    affected_scope=database_scope,
                    containment="Migracao reversivel ou janela de manutencao.",
                    rollback_requirement="required",
                    verification=["migracao aplicada e revertida em ambiente equivalente"],
                    residual_risk=RiskSeverity.MEDIUM,
                    confidence=0.8,
                )
            )

        if required_tests:
            scenarios.append(
                ScenarioSimulation(
                    scenario="test_failure",
                    severity=RiskSeverity.MEDIUM,
                    trigger_codes=["REQUIRED_TEST_FAILED"],
                    expected_effect="Teste exigido falha e a mudanca nao pode ser aprovada.",
                    preconditions=["teste declarado como obrigatorio"],
                    affected_scope=required_tests,
                    containment="Nao promover enquanto o teste falhar.",
                    rollback_requirement="recommended" if mutating else "none",
                    verification=required_tests,
                    residual_risk=RiskSeverity.LOW,
                    confidence=0.75,
                )
            )

        if integrations:
            scenarios.append(
                ScenarioSimulation(
                    scenario="external_service_failure",
                    severity=RiskSeverity.MEDIUM,
                    trigger_codes=["EXTERNAL_SERVICE_FAILURE"],
                    expected_effect=(
                        "Integracao externa indisponivel deixa efeito parcial fora do sistema."
                    ),
                    preconditions=["integracao externa declarada"],
                    affected_scope=integrations,
                    containment="Efeito externo nao e revertido pelo rollback local.",
                    rollback_requirement="required" if mutating else "recommended",
                    verification=["conciliacao com o servico externo"],
                    residual_risk=RiskSeverity.MEDIUM,
                    confidence=0.6,
                )
            )

        return scenarios

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
        analysis = PreExecutionRiskAnalysis(
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
        # Stage R2: o dominio Risk passa a guardar a propria previsao. Falha de
        # persistencia NAO altera a analise — registrar e efeito colateral, e um
        # motor de risco que para de analisar porque o banco caiu seria pior do
        # que um motor sem historico.
        try:
            risk_persistence_service.record_analysis(analysis)
        except RiskRepositoryError:
            pass
        return analysis


pre_execution_risk_service = PreExecutionRiskService()
