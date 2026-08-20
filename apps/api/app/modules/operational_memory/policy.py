from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from app.modules.operational_memory.schemas import (
    CandidateDecision,
    ConfidenceBreakdown,
    EvidenceEffect,
    EvidenceReference,
    MemoryLifecycle,
    PatternType,
)

OPERATIONAL_MEMORY_POLICY_VERSION = "operational-memory-v1"
PROMOTION_MIN_DISTINCT_SUPPORT = 3
PROMOTION_CONFIDENCE = 0.70
RISK_PATTERN_TYPES = {
    PatternType.FAILURE_PATTERN,
    PatternType.ANTI_PATTERN,
    PatternType.RISK_PATTERN,
}


@dataclass(frozen=True)
class PolicyAssessment:
    confidence: float
    breakdown: ConfidenceBreakdown
    lifecycle: MemoryLifecycle
    decision: CandidateDecision
    reason: str


def stable_pattern_id(
    project_id: str,
    pattern_type: PatternType,
    pattern_key: str,
    task_type: str,
) -> str:
    material = "|".join((project_id, pattern_type.value, pattern_key, task_type)).encode("utf-8")
    return f"pattern-{hashlib.sha256(material).hexdigest()[:32]}"


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _recency(evidence: list[EvidenceReference], now: datetime) -> float:
    values: list[float] = []
    for item in evidence:
        observed = item.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - observed).total_seconds() / 86_400)
        values.append(max(0.0, 1.0 - min(age_days, 365.0) / 365.0))
    return _average(values)


def assess_pattern(
    *,
    pattern_type: PatternType,
    evidence: list[EvidenceReference],
    current_lifecycle: MemoryLifecycle | None,
    now: datetime | None = None,
) -> PolicyAssessment:
    reference = now or datetime.now(timezone.utc)
    positive = [
        item
        for item in evidence
        if item.effect
        in {EvidenceEffect.SUPPORTS, EvidenceEffect.MITIGATES, EvidenceEffect.RESOLVES}
    ]
    supports = [item for item in evidence if item.effect is EvidenceEffect.SUPPORTS]
    contradictions = [item for item in evidence if item.effect is EvidenceEffect.CONTRADICTS]
    distinct_support = {(item.source_type.value, item.source_id) for item in supports}
    source_reliability = _average([item.source_reliability for item in positive])
    evidence_strength = _average([item.evidence_strength for item in positive])
    frequency = min(1.0, len(distinct_support) / PROMOTION_MIN_DISTINCT_SUPPORT)
    recency = _recency(positive, reference)
    context_match = _average([item.context_match for item in positive])
    qa_validation = 1.0 if any(item.qa_validated for item in positive) else 0.0
    human_validation = 1.0 if any(item.human_validated for item in positive) else 0.0
    contradiction_penalty = min(
        0.4,
        len(contradictions) / max(1, len(evidence)) * 0.4,
    )
    confidence = round(
        max(
            0.0,
            min(
                1.0,
                0.20 * source_reliability
                + 0.20 * evidence_strength
                + 0.20 * frequency
                + 0.10 * recency
                + 0.15 * context_match
                + 0.10 * qa_validation
                + 0.05 * human_validation
                - contradiction_penalty,
            ),
        ),
        4,
    )
    breakdown = ConfidenceBreakdown(
        source_reliability=round(source_reliability, 4),
        evidence_strength=round(evidence_strength, 4),
        frequency=round(frequency, 4),
        recency=round(recency, 4),
        context_match=round(context_match, 4),
        qa_validation=qa_validation,
        human_validation=human_validation,
        contradiction_penalty=round(contradiction_penalty, 4),
    )

    verified_resolution = pattern_type in RISK_PATTERN_TYPES and any(
        item.effect is EvidenceEffect.RESOLVES and (item.qa_validated or item.human_validated)
        for item in evidence
    )
    verified_mitigation = pattern_type in RISK_PATTERN_TYPES and any(
        item.effect is EvidenceEffect.MITIGATES and (item.qa_validated or item.human_validated)
        for item in evidence
    )

    if verified_resolution:
        lifecycle = MemoryLifecycle.RESOLVED
        decision = CandidateDecision.RESOLVED
        reason = "Evidência posterior QA/humana validada resolveu o padrão de risco."
    elif current_lifecycle is MemoryLifecycle.RESOLVED:
        lifecycle = MemoryLifecycle.RESOLVED
        decision = CandidateDecision.DETECTED
        reason = "Padrão permanece resolvido; nova evidência foi preservada para revisão."
    elif verified_mitigation:
        lifecycle = MemoryLifecycle.MITIGATED
        decision = CandidateDecision.MITIGATED
        reason = "Evidência posterior QA/humana validada mitigou o padrão de risco."
    elif current_lifecycle is MemoryLifecycle.MITIGATED:
        lifecycle = MemoryLifecycle.MITIGATED
        decision = CandidateDecision.DETECTED
        reason = "Padrão permanece mitigado; nova evidência foi preservada para revisão."
    elif (
        len(distinct_support) >= PROMOTION_MIN_DISTINCT_SUPPORT
        and confidence >= PROMOTION_CONFIDENCE
    ):
        lifecycle = MemoryLifecycle.ACTIVE
        decision = CandidateDecision.PROMOTED
        reason = "Evidência distinta e confiança atingiram a política de promoção."
    else:
        lifecycle = MemoryLifecycle.DETECTED
        decision = CandidateDecision.DETECTED
        reason = "Evidência insuficiente para promoção; padrão permanece detectado."

    return PolicyAssessment(
        confidence=confidence,
        breakdown=breakdown,
        lifecycle=lifecycle,
        decision=decision,
        reason=reason,
    )
