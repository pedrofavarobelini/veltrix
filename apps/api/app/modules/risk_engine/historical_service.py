from __future__ import annotations

import hashlib
import json
from collections import Counter

from app.modules.operational_memory.schemas import EvidenceSourceType, PatternType
from app.modules.operational_memory.service import operational_memory_service
from app.modules.report_memory.service import report_memory_service
from app.modules.retrieval.schemas import RetrievalQuery
from app.modules.retrieval.service import retrieval_service
from app.modules.risk_engine.historical_schemas import (
    BenchmarkCase,
    CasePrediction,
    ExcludedHistoricalSample,
    HistoricalBenchmarkRequest,
    HistoricalBenchmarkResult,
    HistoricalRiskQuery,
    HistoricalRiskSummary,
    HistoricalSample,
    RiskStrategy,
    StrategyMetrics,
)
from app.modules.risk_engine.rules import evaluate_deterministic_rules
from app.modules.risk_engine.schemas import RiskSeverity
from app.modules.risk_engine.service import risk_engine_foundation_service

_RISK_PATTERNS = {
    PatternType.FAILURE_PATTERN,
    PatternType.ANTI_PATTERN,
    PatternType.RISK_PATTERN,
}


def _stable_benchmark_id(payload: HistoricalBenchmarkRequest) -> str:
    encoded = json.dumps(
        payload.model_dump(mode="json", exclude={"benchmark_id"}),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "benchmark_" + hashlib.sha256(encoded).hexdigest()[:24]


class HistoricalRiskService:
    @staticmethod
    def _risk_policies(project_id: str, memory) -> list[str]:
        policies: set[str] = set()
        for evidence in memory.evidence:
            if evidence.source_type is not EvidenceSourceType.REPORT:
                continue
            report = report_memory_service.get_report(project_id, evidence.source_id)
            if report is None or not report.metadata:
                continue
            policy = report.metadata.get("risk_policy_version")
            if isinstance(policy, str) and policy:
                policies.add(policy)
        return sorted(policies)

    def summarize(self, query: HistoricalRiskQuery) -> HistoricalRiskSummary:
        project_id = query.project_id.strip().lower()
        repository = operational_memory_service.repository_for_retrieval()
        filters = {
            "task_types": sorted(set(query.task_types)),
            "pattern_types": sorted(item.value for item in query.pattern_types),
            "lifecycles": sorted(item.value for item in query.lifecycles),
            "min_confidence": query.min_confidence,
            "risk_policy_versions": sorted(set(query.risk_policy_versions)),
        }
        if repository is None:
            return HistoricalRiskSummary(
                status="disabled",
                project_id=project_id,
                risk_policy_versions=sorted(set(query.risk_policy_versions)),
                window_start=query.window_start,
                window_end=query.window_end,
                filters=filters,
                sample_size=0,
                excluded_count=0,
                average_confidence=0.0,
            )
        memories = repository.list_memory(project_id, limit=query.max_samples)
        samples: list[HistoricalSample] = []
        excluded: list[ExcludedHistoricalSample] = []
        requested_policies = set(query.risk_policy_versions)
        for memory in memories:
            if not (query.window_start <= memory.updated_at <= query.window_end):
                continue
            if query.task_types and memory.pattern.task_type not in set(query.task_types):
                continue
            if query.pattern_types and memory.pattern.pattern_type not in set(query.pattern_types):
                continue
            if query.lifecycles and memory.lifecycle not in set(query.lifecycles):
                continue
            if memory.confidence < query.min_confidence:
                continue
            policies = self._risk_policies(project_id, memory)
            if len(policies) > 1:
                excluded.append(
                    ExcludedHistoricalSample(
                        memory_id=memory.memory_id,
                        reason_code="INCOMPATIBLE_POLICY_MIX",
                        observed_policy_versions=policies,
                    )
                )
                continue
            if not policies:
                excluded.append(
                    ExcludedHistoricalSample(
                        memory_id=memory.memory_id,
                        reason_code="RISK_POLICY_UNKNOWN",
                    )
                )
                continue
            if not requested_policies.intersection(policies):
                excluded.append(
                    ExcludedHistoricalSample(
                        memory_id=memory.memory_id,
                        reason_code="RISK_POLICY_NOT_REQUESTED",
                        observed_policy_versions=policies,
                    )
                )
                continue
            outcome_class = (
                "risk" if memory.pattern.pattern_type in _RISK_PATTERNS else "success"
            )
            samples.append(
                HistoricalSample(
                    memory_id=memory.memory_id,
                    pattern_type=memory.pattern.pattern_type,
                    lifecycle=memory.lifecycle,
                    task_type=memory.pattern.task_type,
                    confidence=memory.confidence,
                    evidence_count=memory.sample_size,
                    updated_at=memory.updated_at,
                    operational_memory_policy_version=memory.policy_version,
                    risk_policy_versions=policies,
                    outcome_class=outcome_class,
                )
            )
        outcomes = Counter(item.outcome_class for item in samples)
        sample_size = len(samples)
        average = (
            round(sum(item.confidence for item in samples) / sample_size, 6)
            if sample_size
            else 0.0
        )
        return HistoricalRiskSummary(
            project_id=project_id,
            risk_policy_versions=sorted(requested_policies),
            window_start=query.window_start,
            window_end=query.window_end,
            filters=filters,
            sample_size=sample_size,
            excluded_count=len(excluded),
            outcomes=dict(sorted(outcomes.items())),
            average_confidence=average,
            generalizable=sample_size >= 30,
            small_sample_warning=sample_size < 30,
            samples=samples,
            excluded_samples=excluded,
        )

    @staticmethod
    def _history_prediction(case: BenchmarkCase, allowed_ids: set[str]) -> CasePrediction:
        request = case.request
        result = retrieval_service.retrieve(
            RetrievalQuery(
                query_id=f"history-{case.case_id}",
                producer=request.producer,
                project_id=request.project_id,
                keywords=[
                    request.requested_operation.kind.value.lower(),
                    *[item[:64] for item in request.requested_operation.targets[:11]],
                ],
                include_anti_patterns=True,
                max_results=5,
                max_context_chars=2000,
            )
        )
        compatible = [item for item in result.items if item.memory_id in allowed_ids]
        if not compatible:
            return CasePrediction(
                case_id=case.case_id,
                predicted_risk=None,
                confidence=0.0,
                reason_codes=["HISTORY_ABSTAINED"],
            )
        risky = [item for item in compatible if item.pattern_type in _RISK_PATTERNS]
        evidence = risky or compatible
        confidence = max(item.confidence * item.relevance_score for item in evidence)
        return CasePrediction(
            case_id=case.case_id,
            predicted_risk=bool(risky),
            confidence=round(confidence, 6),
            reason_codes=sorted({item.pattern_type.value for item in evidence}),
        )

    @staticmethod
    def _metrics(
        strategy: RiskStrategy,
        cases: list[BenchmarkCase],
        predictions: list[CasePrediction],
    ) -> StrategyMetrics:
        tp = fp = tn = fn = severe_fn = abstentions = 0
        weighted = 0.0
        calibration: list[float] = []
        by_id = {item.case_id: item for item in cases}
        for prediction in predictions:
            case = by_id[prediction.case_id]
            if prediction.predicted_risk is None:
                abstentions += 1
                continue
            probability = prediction.confidence if prediction.predicted_risk else 1 - prediction.confidence
            calibration.append((probability - float(case.actual_risk)) ** 2)
            if prediction.predicted_risk and case.actual_risk:
                tp += 1
            elif prediction.predicted_risk and not case.actual_risk:
                fp += 1
                weighted += 1.0
            elif not prediction.predicted_risk and not case.actual_risk:
                tn += 1
            else:
                fn += 1
                severe_fn += int(case.severe_actual)
                weighted += 5.0 if case.severe_actual else 2.0
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        return StrategyMetrics(
            strategy=strategy,
            sample_size=len(cases),
            abstentions=abstentions,
            true_positive=tp,
            false_positive=fp,
            true_negative=tn,
            false_negative=fn,
            severe_false_negative=severe_fn,
            precision=round(precision, 6),
            recall=round(recall, 6),
            severity_weighted_errors=weighted,
            calibration_error=(
                round(sum(calibration) / len(calibration), 6) if calibration else 0.0
            ),
            review_abstention_rate=round(abstentions / len(cases), 6),
            predictions=predictions,
        )

    def benchmark(self, request: HistoricalBenchmarkRequest) -> HistoricalBenchmarkResult:
        summary = self.summarize(
            HistoricalRiskQuery(
                producer=request.producer,
                project_id=request.project_id,
                window_start=request.window_start,
                window_end=request.window_end,
                risk_policy_versions=[request.risk_policy_version],
            )
        )
        allowed_ids = {item.memory_id for item in summary.samples}
        predictions: dict[str, list[CasePrediction]] = {
            "deterministic_only": [],
            "semantic_only": [],
            "history_only": [],
            "hybrid": [],
        }
        for case in request.cases:
            rules = evaluate_deterministic_rules(case.request)
            deterministic_risk = any(
                item.severity in {RiskSeverity.HIGH, RiskSeverity.CRITICAL} for item in rules
            )
            deterministic_confidence = (
                max((1.0 if item.severity is RiskSeverity.CRITICAL else 0.8 for item in rules), default=0.7)
            )
            deterministic = CasePrediction(
                case_id=case.case_id,
                predicted_risk=deterministic_risk,
                confidence=deterministic_confidence,
                reason_codes=sorted(item.reason_code for item in rules),
            )
            foundation = risk_engine_foundation_service.analyze(case.request)
            semantic_risk = any(
                item.severity in {RiskSeverity.HIGH, RiskSeverity.CRITICAL}
                for item in foundation.signals
            )
            semantic = CasePrediction(
                case_id=case.case_id,
                predicted_risk=semantic_risk,
                confidence=max(0.5, foundation.confidence),
                reason_codes=sorted(item.code for item in foundation.signals),
            )
            history = self._history_prediction(case, allowed_ids)
            hybrid_risk = deterministic_risk or semantic_risk or history.predicted_risk is True
            hybrid = CasePrediction(
                case_id=case.case_id,
                predicted_risk=hybrid_risk,
                confidence=max(
                    deterministic.confidence if deterministic_risk else 0.0,
                    semantic.confidence if semantic_risk else 0.0,
                    history.confidence,
                    0.7 if not hybrid_risk else 0.0,
                ),
                reason_codes=sorted(
                    set(deterministic.reason_codes)
                    | set(semantic.reason_codes)
                    | set(history.reason_codes)
                ),
            )
            predictions["deterministic_only"].append(deterministic)
            predictions["semantic_only"].append(semantic)
            predictions["history_only"].append(history)
            predictions["hybrid"].append(hybrid)
        strategies: tuple[RiskStrategy, ...] = (
            "deterministic_only",
            "semantic_only",
            "history_only",
            "hybrid",
        )
        metrics = [
            self._metrics(strategy, request.cases, predictions[strategy])
            for strategy in strategies
        ]
        tie_priority = {"hybrid": 0, "deterministic_only": 1, "semantic_only": 2, "history_only": 3}
        recommended = min(
            metrics,
            key=lambda item: (
                item.severe_false_negative,
                item.false_negative,
                item.severity_weighted_errors,
                -item.recall,
                tie_priority[item.strategy],
            ),
        )
        return HistoricalBenchmarkResult(
            benchmark_id=request.benchmark_id or _stable_benchmark_id(request),
            project_id=request.project_id.strip().lower(),
            risk_policy_version=request.risk_policy_version,
            historical_summary=summary,
            strategies=metrics,
            recommended_strategy=recommended.strategy,
            recommendation_basis=[
                "MINIMIZE_SEVERE_FALSE_NEGATIVES",
                "MINIMIZE_FALSE_NEGATIVES",
                "MINIMIZE_SEVERITY_WEIGHTED_ERRORS",
                "MAXIMIZE_RECALL",
            ],
        )


historical_risk_service = HistoricalRiskService()
