import pytest
from pydantic import ValidationError

from app.modules.report_intelligence.schemas import TechnicalReportInput
from app.modules.report_intelligence.service import report_intelligence_service


def _report(**overrides) -> TechnicalReportInput:
    base = {
        "project_id": "finguard",
        "report_type": "qa_run",
        "status": "passed",
        "summary": "Execução concluída.",
    }
    base.update(overrides)
    return TechnicalReportInput(**base)


def _signal_types(report: TechnicalReportInput) -> set[str]:
    return {
        signal.signal_type
        for signal in report_intelligence_service.extract_signals(report)
    }


def _signal(report: TechnicalReportInput, signal_type: str):
    for signal in report_intelligence_service.extract_signals(report):
        if signal.signal_type == signal_type:
            return signal
    return None


def test_technical_report_requires_mandatory_fields():
    with pytest.raises(ValidationError):
        TechnicalReportInput(project_id="finguard", report_type="qa_run")

    with pytest.raises(ValidationError):
        TechnicalReportInput(project_id="", report_type="qa_run", status="passed")


def test_passed_report_extracts_qa_passed():
    signal = _signal(_report(status="passed"), "qa_passed")

    assert signal is not None
    assert signal.severity in {"info", "low"}


def test_failed_report_extracts_qa_failed_high():
    signal = _signal(_report(status="failed"), "qa_failed")

    assert signal is not None
    assert signal.severity == "high"


def test_provider_real_used_is_critical():
    report = _report(safety_flags=["provider_real_used"])
    signal = _signal(report, "provider_real_used")

    assert signal is not None
    assert signal.severity == "critical"


def test_provider_real_blocked_is_info():
    report = _report(findings=["Provider real bloqueado pelo safe mode."])
    signal = _signal(report, "provider_real_blocked")

    assert signal is not None
    assert signal.severity == "info"


def test_database_safety_risk_is_critical():
    report = _report(findings=["Banco real foi usado durante o teste."])
    signal = _signal(report, "database_safety_risk")

    assert signal is not None
    assert signal.severity == "critical"


def test_database_safety_ok_takes_precedence_over_risk():
    report = _report(findings=["Banco real não foi usado."])
    types = _signal_types(report)

    assert "database_safety_ok" in types
    assert "database_safety_risk" not in types


def test_smoke_coverage_detected_from_summary():
    report = _report(summary="Suite smoke executada com sucesso.")
    signal = _signal(report, "smoke_coverage")

    assert signal is not None
    assert signal.severity == "medium"


def test_full_coverage_detected_from_findings():
    report = _report(findings=["Cobertura full executada."])
    signal = _signal(report, "full_coverage")

    assert signal is not None
    assert signal.severity == "info"


def test_human_review_required_detected():
    report = _report(findings=["can_advance=false, review_required"])

    assert "human_review_required" in _signal_types(report)


def test_qa_risk_critical_does_not_invalidate_passed_suite():
    report = _report(status="passed", safety_flags=["QA_RISK_CRITICAL"])
    types = _signal_types(report)

    assert "architecture_risk" in types
    assert "qa_passed" in types
    assert "qa_failed" not in types


def test_normalize_report_is_deterministic_and_trims():
    report = TechnicalReportInput(
        project_id="  FinGuard  ",
        report_type=" QA_Run ",
        status=" PASSED ",
        summary="  ok  ",
        findings=["  a  ", "a", "", "b"],
    )
    normalized = report_intelligence_service.normalize_report(report)

    assert normalized.project_id == "finguard"
    assert normalized.report_type == "qa_run"
    assert normalized.status == "passed"
    assert normalized.findings == ["a", "b"]


def test_memory_summary_aggregates_without_persisting():
    reports = [
        _report(status="failed", next_steps=["Corrigir teste X"], created_at="2026-07-01"),
        _report(status="passed", next_steps=["Rodar suíte full"], created_at="2026-07-02"),
    ]

    summary = report_intelligence_service.summarize_memory("finguard", reports)

    assert summary.project_id == "finguard"
    assert summary.last_known_status == "passed"
    assert "Corrigir teste X" in summary.next_recommended_steps
    assert "Rodar suíte full" in summary.next_recommended_steps
    assert summary.updated_at == "2026-07-02"
    assert any("falha" in risk.lower() for risk in summary.unresolved_risks)
    assert summary.completed_milestones != []


def test_memory_summary_ignores_other_projects():
    reports = [_report(project_id="outro-projeto")]

    summary = report_intelligence_service.summarize_memory("finguard", reports)

    assert summary.project_id == "finguard"
    assert summary.last_known_status == "unknown"
    assert summary.important_signals == []
