from app.modules.artifacts.schemas import ArtifactInput
from app.modules.artifacts.service import VISUAL_NOT_SUPPORTED_WARNING, artifact_service
from app.modules.qa_response.service import (
    QA_NO_ARTIFACTS_WARNING,
    QA_SKELETON_WARNING,
    qa_response_service,
)

EMPTY_ARTIFACTS = artifact_service.process(None)


def test_qa_task_returns_not_analyzed_skeleton():
    skeleton = qa_response_service.build_skeleton(
        task_type="qa_report_analysis",
        fallback_used=False,
        artifacts_result=EMPTY_ARTIFACTS,
    )

    assert skeleton is not None
    assert skeleton.status == "not_analyzed"
    assert skeleton.risk_level == "unknown"
    assert skeleton.can_advance is not True
    assert skeleton.confidence == 0.0
    assert skeleton.findings == []
    assert skeleton.failures == []
    assert QA_SKELETON_WARNING in skeleton.warnings
    assert QA_NO_ARTIFACTS_WARNING in skeleton.warnings


def test_non_qa_task_returns_none():
    skeleton = qa_response_service.build_skeleton(
        task_type="general_chat",
        fallback_used=False,
        artifacts_result=EMPTY_ARTIFACTS,
    )

    assert skeleton is None


def test_fallback_adds_critical_warning_to_skeleton():
    skeleton = qa_response_service.build_skeleton(
        task_type="release_gate_review",
        fallback_used=True,
        artifacts_result=EMPTY_ARTIFACTS,
    )

    assert skeleton is not None
    assert any("Fallback Mock usado em tarefa crítica" in w for w in skeleton.warnings)
    assert skeleton.can_advance is not True


def test_visual_artifact_warning_propagates_to_skeleton():
    artifacts_result = artifact_service.process(
        [ArtifactInput(type="screenshot", name="tela.png", content="x")]
    )

    skeleton = qa_response_service.build_skeleton(
        task_type="qa_failure_diagnosis",
        fallback_used=False,
        artifacts_result=artifacts_result,
    )

    assert skeleton is not None
    assert VISUAL_NOT_SUPPORTED_WARNING in skeleton.warnings
