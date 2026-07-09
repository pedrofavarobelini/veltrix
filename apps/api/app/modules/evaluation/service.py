import re

from app.modules.evaluation.schemas import EvaluationCheck, EvaluationResult
from app.modules.intelligence_layer.schemas import IntelligencePlan
from app.modules.report_intelligence.schemas import ReportSignal

# Evaluation Foundation (PEDROCORE-MODEL-FOUNDATION-01).
#
# Avaliação determinística de planos e sinais: mede segurança, coerência e
# compatibilidade com as políticas do PedroCore. Não chama IA externa, não
# faz benchmark de LLM e não substitui revisão humana em fluxo crítico.

_AUTO_TRAINING_PATTERNS = [
    r"auto[-\s]?training",
    r"self[-\s]?training",
    r"autoaprendizado",
    r"auto[-\s]?aprendizado",
    r"treinamento autom[áa]tico",
    r"\btreinar (o )?modelo\b",
    r"\btrain (the )?model\b",
]

_FINETUNING_PATTERNS = [
    r"fine[-\s]?tun(e|ing)",
    r"\bfinetun(e|ing)\b",
    r"ajuste fino do modelo",
]

_SENSITIVE_ENV_PATTERNS = [
    r"\.env\b",
    r"api[_\s-]?key",
    r"\bsecret\b",
    r"\bsenha\b",
    r"\bpassword\b",
    r"\btoken\b",
]

_RISK_ORDER = ["none", "low", "medium", "high", "critical"]

_SEVERITY_TO_RISK = {
    "info": "low",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "error": "high",
    "critical": "critical",
}


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _max_risk(levels: list[str]) -> str:
    if not levels:
        return "none"
    return max(levels, key=_RISK_ORDER.index)


class EvaluationService:
    def evaluate_intelligence_plan(self, plan: IntelligencePlan) -> EvaluationResult:
        """Avalia se um IntelligencePlan respeita as políticas da fundação."""
        plan_text = "\n".join(
            [
                plan.task_type,
                plan.response_profile,
                *plan.safety_flags,
                *plan.instructions,
                *plan.memory_hints,
                *plan.evaluation_hints,
            ]
        )

        checks = [
            EvaluationCheck(
                name="provider_real_not_allowed_by_default",
                passed=not plan.context_policy.allow_real_provider,
                severity="critical",
                message=(
                    "Plano mantém provider real bloqueado por padrão."
                    if not plan.context_policy.allow_real_provider
                    else "Plano tentou habilitar provider real; proibido."
                ),
            ),
            EvaluationCheck(
                name="no_auto_training_claim",
                passed=not _matches_any(_AUTO_TRAINING_PATTERNS, plan_text),
                severity="critical",
                message=(
                    "Plano não contém alegação de autoaprendizado/treinamento."
                    if not _matches_any(_AUTO_TRAINING_PATTERNS, plan_text)
                    else "Plano contém alegação de treinamento/autoaprendizado; proibido."
                ),
            ),
            EvaluationCheck(
                name="no_finetuning_claim",
                passed=not _matches_any(_FINETUNING_PATTERNS, plan_text),
                severity="critical",
                message=(
                    "Plano não contém alegação de fine-tuning."
                    if not _matches_any(_FINETUNING_PATTERNS, plan_text)
                    else "Plano contém alegação de fine-tuning; proibido."
                ),
            ),
            EvaluationCheck(
                name="no_sensitive_env_exposure",
                passed=not _matches_any(_SENSITIVE_ENV_PATTERNS, plan_text)
                and plan.context_policy.sensitive_data_policy in {"sanitize", "block"},
                severity="critical",
                message=(
                    "Plano não referencia .env/segredos e sanitiza dados sensíveis."
                    if not _matches_any(_SENSITIVE_ENV_PATTERNS, plan_text)
                    else "Plano referencia .env/segredos; proibido."
                ),
            ),
            EvaluationCheck(
                name="requires_human_review_for_critical",
                passed=(
                    plan.response_profile != "release_gate_strict"
                    or plan.context_policy.requires_human_review
                ),
                severity="high",
                message=(
                    "Fluxo crítico exige revisão humana conforme esperado."
                    if plan.response_profile != "release_gate_strict"
                    or plan.context_policy.requires_human_review
                    else "Fluxo release_gate_strict sem revisão humana; proibido."
                ),
            ),
            EvaluationCheck(
                name="report_memory_is_not_training",
                passed=not any(
                    _matches_any(_AUTO_TRAINING_PATTERNS + _FINETUNING_PATTERNS, hint)
                    for hint in plan.memory_hints
                ),
                severity="critical",
                message=(
                    "Memory hints não tratam relatórios como treinamento."
                    if not any(
                        _matches_any(
                            _AUTO_TRAINING_PATTERNS + _FINETUNING_PATTERNS, hint
                        )
                        for hint in plan.memory_hints
                    )
                    else "Memory hints tratam relatórios como treinamento; proibido."
                ),
            ),
        ]

        failed = [check for check in checks if not check.passed]
        risk_level = _max_risk(
            [_SEVERITY_TO_RISK.get(check.severity, "medium") for check in failed]
        )

        return EvaluationResult(
            passed=not failed,
            checks=checks,
            requires_human_review=bool(failed)
            or plan.context_policy.requires_human_review,
            risk_level=risk_level,
        )

    def evaluate_report_signals(self, signals: list[ReportSignal]) -> EvaluationResult:
        """Avalia sinais extraídos: críticos/altos sempre exigem revisão humana."""
        checks: list[EvaluationCheck] = []

        critical_signals = [s for s in signals if s.severity == "critical"]
        high_signals = [s for s in signals if s.severity == "high"]

        checks.append(
            EvaluationCheck(
                name="critical_signals_require_human_review",
                passed=not critical_signals,
                severity="critical",
                message=(
                    "Nenhum sinal crítico detectado."
                    if not critical_signals
                    else f"{len(critical_signals)} sinal(is) crítico(s); "
                    "revisão humana obrigatória."
                ),
            )
        )

        provider_real_used = any(
            s.signal_type == "provider_real_used" for s in signals
        )
        checks.append(
            EvaluationCheck(
                name="no_unauthorized_real_provider_usage",
                passed=not provider_real_used,
                severity="critical",
                message=(
                    "Nenhum uso de provider real reportado."
                    if not provider_real_used
                    else "Uso de provider real reportado; exige revisão humana."
                ),
            )
        )

        failed = [check for check in checks if not check.passed]
        risk_levels = [
            _SEVERITY_TO_RISK.get(s.severity, "low")
            for s in signals
            if s.severity in {"medium", "high", "critical"}
        ]

        return EvaluationResult(
            passed=not failed,
            checks=checks,
            requires_human_review=bool(critical_signals or high_signals),
            risk_level=_max_risk(risk_levels),
        )


evaluation_service = EvaluationService()
