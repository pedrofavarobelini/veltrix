from fastapi.testclient import TestClient

from app.main import app
from app.modules.artifacts.schemas import ArtifactInput
from app.modules.artifacts.service import artifact_service
from app.modules.qa_analysis.service import qa_text_analyzer
from app.modules.qa_response.service import qa_response_service

client = TestClient(app)

CLEAN_SUCCESS = "All tests passed. 0 failed. Build successful."


def gate_for(
    content: str | None,
    fallback_used: bool = False,
    safe_mode_blocked: bool = False,
    provider_used: str = "local_qa",
):
    artifacts = (
        [ArtifactInput(type="qa_report", name="qa.md", content=content)]
        if content is not None
        else None
    )
    artifacts_result = artifact_service.process(artifacts)
    analysis = qa_text_analyzer.analyze(
        task_type="release_gate_review",
        artifacts_result=artifacts_result,
        fallback_used=fallback_used,
        safe_mode_blocked=safe_mode_blocked,
    )
    return qa_response_service.evaluate_release_gate(
        artifacts_result=artifacts_result,
        analysis=analysis,
        fallback_used=fallback_used,
        safe_mode_blocked=safe_mode_blocked,
        provider_used=provider_used,
    )


def test_gate_blocks_without_artifacts():
    gate = gate_for(None)

    assert gate.can_advance is False
    assert gate.blocked_reason is not None
    assert "RELEASE_GATE_BLOCKED" in gate.warning_codes


def test_gate_blocks_with_path_rejected_artifact():
    artifacts_result = artifact_service.process(
        [ArtifactInput(type="text", content="abc", metadata={"path": "C:\\x.md"})]
    )
    analysis = qa_text_analyzer.analyze(
        task_type="release_gate_review", artifacts_result=artifacts_result
    )
    gate = qa_response_service.evaluate_release_gate(
        artifacts_result=artifacts_result,
        analysis=analysis,
        fallback_used=False,
        safe_mode_blocked=False,
        provider_used="local_qa",
    )

    assert gate.can_advance is False
    assert "caminho de arquivo" in gate.blocked_reason


def test_gate_blocks_with_failure():
    gate = gate_for("2 tests failed com AssertionError")

    assert gate.can_advance is False
    assert gate.blocked_reason is not None


def test_gate_blocks_with_error():
    gate = gate_for("Traceback (most recent call last): TypeError")

    assert gate.can_advance is False


def test_gate_blocks_with_critical_risk():
    gate = gate_for("All tests passed, mas rodou contra banco real de produção")

    assert gate.can_advance is False
    assert gate.risk_level == "critical"


def test_gate_blocks_with_fallback_mock():
    gate = gate_for(CLEAN_SUCCESS, fallback_used=True)

    assert gate.can_advance is False


def test_gate_blocks_with_safe_mode_blocked():
    gate = gate_for(CLEAN_SUCCESS, safe_mode_blocked=True)

    assert gate.can_advance is False


def test_gate_blocks_with_mock_provider_even_on_success():
    gate = gate_for(CLEAN_SUCCESS, provider_used="mock")

    assert gate.can_advance is False
    assert "Mock" in gate.blocked_reason


def test_gate_blocks_without_evidence():
    gate = gate_for("Relatório descritivo sem sinais objetivos.")

    assert gate.can_advance is False


def test_gate_advances_on_clean_local_scenario():
    gate = gate_for(CLEAN_SUCCESS, provider_used="local_qa")

    assert gate.can_advance is True
    assert gate.blocked_reason is None
    assert gate.risk_level == "low"
    assert gate.confidence >= 0.6


def test_gate_api_release_gate_blocked_without_artifacts():
    response = client.post(
        "/api/chat",
        json={
            "message": "Pode liberar a release?",
            "provider": "mock",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["qa_skeleton"]["can_advance"] is False
    assert data["qa_skeleton"]["status"] == "blocked"
    assert data["status"] == "blocked"
    assert data["blocked_reason"] is not None
    assert "RELEASE_GATE_BLOCKED" in data["warning_codes"]


def test_gate_api_advances_with_local_provider_and_clean_report():
    response = client.post(
        "/api/chat",
        json={
            "message": "Pode liberar a release?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "name": "qa.md", "content": CLEAN_SUCCESS}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["provider"] == "local_qa"
    assert data["fallback_used"] is False
    assert data["qa_skeleton"]["can_advance"] is True
    assert data["qa_skeleton"]["analysis_source"] == "local_text_heuristic"
    assert data["status"] == "ok"


def test_gate_api_mock_provider_does_not_release_even_with_clean_report():
    response = client.post(
        "/api/chat",
        json={
            "message": "Pode liberar a release?",
            "provider": "mock",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "name": "qa.md", "content": CLEAN_SUCCESS}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["qa_skeleton"]["can_advance"] is False
    assert data["status"] == "blocked"
    assert "RELEASE_GATE_BLOCKED" in data["warning_codes"]
