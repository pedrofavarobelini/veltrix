from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VISUAL_TYPES = ["screenshot", "image", "pdf", "playwright_trace"]


def post_visual(task_type: str = "qa_report_analysis", artifact_type: str = "screenshot"):
    return client.post(
        "/api/orchestrate",
        json={
            "message": "Analise esta evidência visual",
            "provider": "mock",
            "task_type": task_type,
            "origin_system": "finguard",
            "artifacts": [
                {"type": artifact_type, "name": f"evidencia.{artifact_type}", "content": "fake"}
            ],
        },
    )


def test_all_visual_types_accepted_with_stub_analysis():
    for artifact_type in VISUAL_TYPES:
        response = post_visual(artifact_type=artifact_type)
        data = response.json()

        assert response.status_code == 200, f"tipo: {artifact_type}"
        visual = data["visual_qa_analysis"]
        assert visual is not None, f"tipo: {artifact_type}"
        assert visual["status"] == "not_analyzed"
        assert visual["supported"] is False
        assert visual["mode"] == "stub"
        assert visual["visual_artifact_count"] == 1


def test_visual_stub_generates_warnings():
    data = post_visual().json()

    assert "VISUAL_QA_NOT_ENABLED" in data["warning_codes"]
    assert "VISUAL_QA_REQUIRES_HUMAN_REVIEW" in data["warning_codes"]
    assert "ARTIFACT_VISUAL_UNSUPPORTED" in data["warning_codes"]


def test_visual_requires_human_review_and_never_advances():
    data = post_visual().json()
    visual = data["visual_qa_analysis"]

    assert visual["requires_human_review"] is True
    assert visual["can_advance"] is False
    assert visual["suggested_manual_checks"] != []


def test_no_ocr_provider_or_playwright_attempted():
    data = post_visual().json()
    visual = data["visual_qa_analysis"]

    assert visual["ocr_attempted"] is False
    assert visual["provider_attempted"] is False
    assert visual["playwright_attempted"] is False


def test_release_gate_never_advances_with_visual_only_evidence():
    response = post_visual(task_type="release_gate_review")
    data = response.json()

    assert response.status_code == 200
    assert data["release_gate"]["can_advance"] is False
    assert "VISUAL_QA_BLOCKED_FOR_RELEASE_GATE" in data["warning_codes"]
    assert data["qa"]["can_advance"] is False


def test_no_visual_analysis_for_textual_only_request():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise",
            "provider": "local_qa",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [{"type": "text", "content": "125 passed, 0 failed."}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["visual_qa_analysis"] is None


def test_visual_plus_clean_textual_can_advance_on_textual_evidence():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode avançar?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [
                {"type": "qa_report", "content": "All tests passed. 0 failed. Build successful."},
                {"type": "screenshot", "name": "tela.png", "content": "fake"},
            ],
        },
    )
    data = response.json()

    assert response.status_code == 200
    # Decisão vem da evidência textual limpa; o visual continua exigindo revisão humana.
    assert data["release_gate"]["can_advance"] is True
    assert data["visual_qa_analysis"]["requires_human_review"] is True
    assert "VISUAL_QA_BLOCKED_FOR_RELEASE_GATE" not in data["warning_codes"]
