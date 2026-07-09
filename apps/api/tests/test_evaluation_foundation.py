from app.modules.evaluation.service import evaluation_service
from app.modules.intelligence_layer.schemas import IntelligencePlan
from app.modules.intelligence_layer.service import intelligence_layer_service
from app.modules.project_context.service import project_context_resolver
from app.modules.report_intelligence.schemas import ReportSignal
from app.modules.task_router.service import task_router


def _plan_for(task_type: str) -> IntelligencePlan:
    strategy = task_router.resolve(task_type)
    project = project_context_resolver.resolve("pedrocore")
    return intelligence_layer_service.build_plan(strategy=strategy, project=project)


def _signal(signal_type: str, severity: str) -> ReportSignal:
    return ReportSignal(
        project_id="pedrocore",
        report_type="qa_run",
        signal_type=signal_type,
        severity=severity,
        summary=f"sinal {signal_type}",
    )


def test_clean_plan_without_real_provider_passes():
    result = evaluation_service.evaluate_intelligence_plan(_plan_for("general_chat"))

    assert result.passed is True
    assert result.risk_level == "none"
    check_names = {check.name for check in result.checks}
    assert {
        "provider_real_not_allowed_by_default",
        "no_auto_training_claim",
        "no_finetuning_claim",
        "no_sensitive_env_exposure",
        "requires_human_review_for_critical",
        "report_memory_is_not_training",
    } <= check_names


def test_plan_with_auto_training_claim_fails():
    plan = _plan_for("general_chat")
    plan.instructions.append("Ativar autoaprendizado do modelo em produção.")

    result = evaluation_service.evaluate_intelligence_plan(plan)

    assert result.passed is False
    assert result.requires_human_review is True
    assert result.risk_level == "critical"
    failed = {check.name for check in result.checks if not check.passed}
    assert "no_auto_training_claim" in failed


def test_plan_with_finetuning_claim_fails():
    plan = _plan_for("general_chat")
    plan.memory_hints.append("Usar relatórios para fine-tuning do modelo local.")

    result = evaluation_service.evaluate_intelligence_plan(plan)

    assert result.passed is False
    failed = {check.name for check in result.checks if not check.passed}
    assert "no_finetuning_claim" in failed
    assert "report_memory_is_not_training" in failed


def test_plan_referencing_env_secrets_fails():
    plan = _plan_for("general_chat")
    plan.instructions.append("Ler apps/api/.env para validar a api_key.")

    result = evaluation_service.evaluate_intelligence_plan(plan)

    assert result.passed is False
    failed = {check.name for check in result.checks if not check.passed}
    assert "no_sensitive_env_exposure" in failed


def test_release_gate_plan_passes_with_human_review():
    result = evaluation_service.evaluate_intelligence_plan(
        _plan_for("release_gate_review")
    )

    assert result.passed is True
    assert result.requires_human_review is True


def test_critical_signals_require_human_review():
    result = evaluation_service.evaluate_report_signals(
        [_signal("database_safety_risk", "critical")]
    )

    assert result.passed is False
    assert result.requires_human_review is True
    assert result.risk_level == "critical"


def test_provider_real_used_signal_fails_evaluation():
    result = evaluation_service.evaluate_report_signals(
        [_signal("provider_real_used", "critical")]
    )

    assert result.passed is False
    failed = {check.name for check in result.checks if not check.passed}
    assert "no_unauthorized_real_provider_usage" in failed


def test_info_signals_pass_without_human_review():
    result = evaluation_service.evaluate_report_signals(
        [_signal("qa_passed", "info"), _signal("provider_real_blocked", "info")]
    )

    assert result.passed is True
    assert result.requires_human_review is False
    assert result.risk_level == "none"
