from __future__ import annotations

import hashlib
import json

from app.modules.risk_engine.analyzers import (
    AmbiguityDetector,
    ContextResolver,
    IntentAnalyzer,
    PromptQualityAnalyzer,
    ScopeAnalyzer,
)
from app.modules.risk_engine.schemas import (
    RiskAssessment,
    RiskFinding,
    RiskRequest,
    RiskSeverity,
    RiskSignal,
)


def _stable_id(prefix: str, *values: object) -> str:
    encoded = json.dumps(values, ensure_ascii=True, sort_keys=True, default=str).encode()
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:24]}"


class RiskEngineFoundationService:
    """Deterministic analysis only. No target-operation adapter exists here."""

    def __init__(self) -> None:
        self._intent = IntentAnalyzer()
        self._context = ContextResolver()
        self._quality = PromptQualityAnalyzer()
        self._ambiguity = AmbiguityDetector()
        self._scope = ScopeAnalyzer()

    @staticmethod
    def _signal(
        request_id: str,
        code: str,
        category: str,
        severity: RiskSeverity,
        detail: str,
    ) -> RiskSignal:
        return RiskSignal(
            signal_id=_stable_id("sig", request_id, code, category),
            code=code,
            category=category,
            severity=severity,
            detail=detail,
        )

    def analyze(self, request: RiskRequest) -> RiskAssessment:
        intent = self._intent.analyze(request)
        context = self._context.resolve(request)
        quality = self._quality.analyze(intent, context)
        ambiguity = self._ambiguity.analyze(intent, context)
        scope = self._scope.analyze(intent, context)
        signals: list[RiskSignal] = []
        if not intent.intent_consistent:
            signals.append(
                self._signal(
                    request.request_id,
                    "INTENT_CONFLICT",
                    "intent",
                    RiskSeverity.HIGH,
                    "A operação estruturada diverge da operação inferida do pedido.",
                )
            )
        if context.missing_context:
            signals.append(
                self._signal(
                    request.request_id,
                    "CONTEXT_INCOMPLETE",
                    "context",
                    RiskSeverity.MEDIUM,
                    "Contexto obrigatório ausente: " + ", ".join(context.missing_context),
                )
            )
        if quality.score < 0.67:
            signals.append(
                self._signal(
                    request.request_id,
                    "PROMPT_QUALITY_LOW",
                    "prompt_quality",
                    RiskSeverity.MEDIUM,
                    "O pedido não delimita operação, escopo, validação e reversão suficientes.",
                )
            )
        if scope.forbidden_targets:
            signals.append(
                self._signal(
                    request.request_id,
                    "FORBIDDEN_SCOPE_REQUESTED",
                    "scope",
                    RiskSeverity.CRITICAL,
                    "A operação inclui alvo explicitamente proibido.",
                )
            )
        if scope.targets_outside_scope or scope.unknown_targets:
            signals.append(
                self._signal(
                    request.request_id,
                    "SCOPE_UNBOUNDED",
                    "scope",
                    RiskSeverity.HIGH,
                    "Um ou mais alvos não pertencem ao escopo permitido conhecido.",
                )
            )
        if intent.destructive:
            signals.append(
                self._signal(
                    request.request_id,
                    "DESTRUCTIVE_INTENT",
                    "intent",
                    RiskSeverity.HIGH,
                    "A intenção declarada pode remover ou tornar dados indisponíveis.",
                )
            )
        if intent.external_effects:
            signals.append(
                self._signal(
                    request.request_id,
                    "EXTERNAL_EFFECTS",
                    "intent",
                    RiskSeverity.HIGH,
                    "A intenção declara efeitos fora do processo local.",
                )
            )

        findings = [
            RiskFinding(
                finding_id=_stable_id("find", request.request_id, signal.code),
                signal_ids=[signal.signal_id],
                title=signal.detail,
                severity=signal.severity,
                reason_code=signal.code,
            )
            for signal in signals
            if signal.severity in {RiskSeverity.MEDIUM, RiskSeverity.HIGH, RiskSeverity.CRITICAL}
        ]
        confidence_parts = (
            float(intent.explicit_intent),
            float(bool(intent.targets)),
            float(bool(context.permissions)),
            float(bool(context.allowed_scope)),
            float(not ambiguity.ambiguous),
        )
        confidence = round(sum(confidence_parts) / len(confidence_parts), 6)
        assessment_id = _stable_id(
            "risk",
            request.model_dump(mode="json"),
            intent.model_dump(mode="json"),
            context.model_dump(mode="json"),
        )
        return RiskAssessment(
            assessment_id=assessment_id,
            request_id=request.request_id,
            project_id=request.project_id.strip().lower(),
            intent=intent,
            resolved_context=context,
            prompt_quality=quality,
            ambiguity=ambiguity,
            scope=scope,
            signals=signals,
            findings=findings,
            confidence=confidence,
            uncertainty=round(1.0 - confidence, 6),
        )


risk_engine_foundation_service = RiskEngineFoundationService()
