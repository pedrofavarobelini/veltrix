import json

from app.modules.artifacts.schemas import ArtifactInput
from app.modules.artifacts.service import artifact_service
from app.modules.qa_analysis.service import qa_text_analyzer

FORBIDDEN_COMMAND_TERMS = [
    "rm ",
    "del ",
    "rmdir",
    "drop",
    "truncate",
    "delete",
    "push",
    "commit",
    "deploy",
]


def analyze_content(
    content: str,
    task_type: str = "qa_report_analysis",
    fallback_used: bool = False,
    safe_mode_blocked: bool = False,
):
    artifacts_result = artifact_service.process(
        [ArtifactInput(type="qa_report", name="relatorio.md", content=content)]
    )
    return qa_text_analyzer.analyze(
        task_type=task_type,
        artifacts_result=artifacts_result,
        fallback_used=fallback_used,
        safe_mode_blocked=safe_mode_blocked,
    )


def test_success_report_detected():
    result = analyze_content("Resultado da suite: 66 passed, 2 warnings")

    assert result.analyzed is True
    assert result.status in {"pass", "warning"}
    assert result.risk_level in {"low", "medium"}
    assert result.confidence > 0


def test_clean_success_allows_advance():
    result = analyze_content("All tests passed. 0 failed. Build successful.")

    assert result.analyzed is True
    assert result.status == "pass"
    assert result.risk_level == "low"
    assert result.can_advance is True
    assert result.confidence >= 0.6
    assert result.confidence < 1.0


def test_failure_detected():
    result = analyze_content("2 tests failed with AssertionError in test_auth")

    assert result.status == "fail"
    assert result.can_advance is False
    assert result.failures != []
    assert result.risk_level in {"high", "critical"}


def test_error_and_traceback_detected():
    result = analyze_content(
        "Traceback (most recent call last):\n  ValueError: invalid input"
    )

    assert result.status == "fail"
    assert result.can_advance is False
    assert "QA_ERROR_DETECTED" in result.warning_codes


def test_warning_only_is_not_critical():
    result = analyze_content("DeprecationWarning: este método está deprecated")

    assert result.analyzed is True
    assert result.status == "warning"
    assert result.risk_level == "medium"
    assert result.risk_level != "critical"
    assert result.can_advance is False


def test_lint_failed_detected():
    result = analyze_content("Pipeline local: lint failed em 3 arquivos")

    assert result.status == "fail"
    assert result.can_advance is False


def test_typecheck_failed_detected():
    result = analyze_content("typecheck failed: 4 issues encontrados")

    assert result.status == "fail"
    assert result.can_advance is False


def test_secret_generates_critical_risk():
    result = analyze_content("Log contém api key exposta e um secret de teste")

    assert result.risk_level == "critical"
    assert result.can_advance is False
    assert "QA_RISK_CRITICAL" in result.warning_codes


def test_env_file_mention_generates_critical_risk():
    result = analyze_content("O relatório menciona o arquivo .env do backend")

    assert result.risk_level == "critical"
    assert result.can_advance is False


def test_production_database_generates_critical_risk():
    result = analyze_content("Teste rodou contra produção usando banco real")

    assert result.risk_level == "critical"
    assert result.can_advance is False


def test_drop_table_generates_critical_risk():
    result = analyze_content("Migration executou DROP TABLE users por engano")

    assert result.risk_level == "critical"
    assert result.can_advance is False


def test_truncate_generates_critical_risk():
    result = analyze_content("Script sugeriu TRUNCATE na tabela de logs")

    assert result.risk_level == "critical"
    assert result.can_advance is False


def test_delete_from_generates_critical_risk():
    result = analyze_content("Query perigosa: DELETE FROM transactions sem WHERE")

    assert result.risk_level == "critical"
    assert result.can_advance is False


def test_no_artifacts_returns_medium_risk_and_blocks():
    artifacts_result = artifact_service.process(None)
    result = qa_text_analyzer.analyze(
        task_type="qa_report_analysis",
        artifacts_result=artifacts_result,
        fallback_used=False,
        safe_mode_blocked=False,
    )

    assert result.analyzed is False
    assert result.status == "not_analyzed"
    assert result.risk_level == "medium"
    assert result.can_advance is False
    assert result.confidence == 0.0


def test_no_evidence_returns_not_analyzed():
    result = analyze_content("Relatório descritivo sem sinais objetivos.")

    assert result.analyzed is False
    assert result.status == "not_analyzed"
    assert result.can_advance is False


def test_non_qa_task_returns_none():
    artifacts_result = artifact_service.process(
        [ArtifactInput(type="markdown", content="All tests passed")]
    )
    result = qa_text_analyzer.analyze(
        task_type="general_chat",
        artifacts_result=artifacts_result,
    )

    assert result is None


def test_fallback_blocks_advance_even_with_clean_success():
    result = analyze_content(
        "All tests passed. 0 failed. Build successful.",
        fallback_used=True,
    )

    assert result.can_advance is False


def test_safe_mode_blocks_advance_even_with_clean_success():
    result = analyze_content(
        "All tests passed. 0 failed. Build successful.",
        safe_mode_blocked=True,
    )

    assert result.can_advance is False


def test_path_rejected_artifact_gives_high_risk():
    artifacts_result = artifact_service.process(
        [
            ArtifactInput(
                type="qa_report",
                name="relatorio.md",
                content="conteudo qualquer",
                metadata={"path": "C:\\qualquer\\arquivo.md"},
            )
        ]
    )
    result = qa_text_analyzer.analyze(
        task_type="qa_report_analysis",
        artifacts_result=artifacts_result,
    )

    assert artifacts_result.path_rejected is True
    assert result.risk_level == "high"
    assert result.can_advance is False


def test_suggested_commands_are_safe_strings():
    result = analyze_content("3 tests failed com traceback no módulo de auth")

    assert result.suggested_commands != []
    for command in result.suggested_commands:
        assert isinstance(command, str)
        lowered = command.lower()
        for term in FORBIDDEN_COMMAND_TERMS:
            assert term not in lowered, f"comando inseguro sugerido: {command}"


def test_secret_value_is_not_echoed_in_result():
    result = analyze_content("password: SuperSenhaUltraSecreta987!")

    dumped = json.dumps(result.model_dump(), ensure_ascii=False).lower()
    assert "supersenhaultrasecreta987" not in dumped
    assert result.risk_level == "critical"
