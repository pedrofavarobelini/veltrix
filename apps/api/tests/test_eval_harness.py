import pytest
from pydantic import ValidationError

from app.modules.eval_harness.fixtures import DEFAULT_EVAL_CASES
from app.modules.eval_harness.schemas import EvalCase
from app.modules.eval_harness.service import eval_harness_service
from app.modules.report_memory.service import FLAG_PERSISTENCE


@pytest.fixture(autouse=True)
def default_env(monkeypatch):
    # Fixtures padrão assumem ambiente default (memória/local model OFF).
    monkeypatch.delenv(FLAG_PERSISTENCE, raising=False)
    monkeypatch.delenv("PEDROCORE_ENABLE_LOCAL_MODEL", raising=False)
    yield


def test_default_fixtures_all_pass():
    result = eval_harness_service.run_sync()

    failed = [c for c in result.cases if not c.passed]
    assert failed == [], f"casos falhando: {[(c.case_id, c.failures) for c in failed]}"
    assert result.total == len(DEFAULT_EVAL_CASES)
    assert result.passed == result.total
    assert result.failed == 0
    assert result.risk_level == "none"


def test_forbidden_pattern_causes_failure():
    case = EvalCase(
        case_id="forbidden-pattern-detected",
        task_type="general_chat",
        input="Teste",
        # O mock em modo técnico sempre menciona 'multi-provider'.
        forbidden_patterns=["multi-provider"],
    )

    result = eval_harness_service.run_sync([case])

    assert result.failed == 1
    assert result.risk_level == "high"
    assert any("padrão proibido" in f for f in result.cases[0].failures)


def test_missing_disclaimer_requirement_causes_failure():
    case = EvalCase(
        case_id="general-chat-has-no-disclaimer",
        task_type="general_chat",
        input="Oi",
        expected_requirements=["não é aconselhamento financeiro definitivo"],
    )

    result = eval_harness_service.run_sync([case])

    assert result.failed == 1
    assert any("requisito ausente" in f for f in result.cases[0].failures)


def test_finance_disclaimer_requirement_passes():
    case = EvalCase(
        case_id="finance-disclaimer-present",
        task_type="finance_advice",
        input="Devo investir tudo?",
        expected_requirements=["não é aconselhamento financeiro definitivo"],
        expected_warnings=["FINANCIAL_DISCLAIMER"],
    )

    result = eval_harness_service.run_sync([case])

    assert result.failed == 0


def test_eval_case_rejects_real_provider():
    with pytest.raises(ValidationError):
        EvalCase(
            case_id="never-real",
            input="Teste",
            allow_real_provider=True,
        )


def test_critical_signals_require_human_review_in_evaluation():
    from app.modules.evaluation.service import evaluation_service
    from app.modules.report_intelligence.schemas import ReportSignal

    result = evaluation_service.evaluate_report_signals(
        [
            ReportSignal(
                project_id="demo",
                report_type="qa_run",
                signal_type="database_safety_risk",
                severity="critical",
                summary="Banco real usado.",
            )
        ]
    )

    assert result.requires_human_review is True
    assert result.risk_level == "critical"
