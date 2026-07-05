from fastapi.testclient import TestClient

from app.main import app
from app.modules.visual_qa.service import evaluate_real_visual_guard

client = TestClient(app)

FLAG_MULTIMODAL = "PEDROCORE_MULTIMODAL_PROVIDER_ENABLED"
FLAG_VISUAL = "PEDROCORE_VISUAL_QA_ENABLED"


def _clear(monkeypatch):
    monkeypatch.delenv(FLAG_MULTIMODAL, raising=False)
    monkeypatch.delenv(FLAG_VISUAL, raising=False)


def test_multimodal_disabled_blocks(monkeypatch):
    _clear(monkeypatch)

    warnings, warning_codes = evaluate_real_visual_guard(allow_real_provider=True)

    assert "MULTIMODAL_PROVIDER_DISABLED" in warning_codes


def test_allow_real_provider_false_blocks(monkeypatch):
    monkeypatch.setenv(FLAG_MULTIMODAL, "true")
    monkeypatch.setenv(FLAG_VISUAL, "true")

    warnings, warning_codes = evaluate_real_visual_guard(allow_real_provider=False)

    assert "MULTIMODAL_PROVIDER_REQUIRES_EXPLICIT_AUTH" in warning_codes


def test_visual_qa_flag_false_blocks(monkeypatch):
    monkeypatch.setenv(FLAG_MULTIMODAL, "true")
    monkeypatch.delenv(FLAG_VISUAL, raising=False)

    warnings, warning_codes = evaluate_real_visual_guard(allow_real_provider=True)

    assert "MULTIMODAL_PROVIDER_REQUIRES_FLAG" in warning_codes


def test_all_flags_true_still_requires_human_confirmation(monkeypatch):
    # Mesmo totalmente autorizado, esta versão não executa envio multimodal:
    # contrato preparado, execução exige frente futura.
    monkeypatch.setenv(FLAG_MULTIMODAL, "true")
    monkeypatch.setenv(FLAG_VISUAL, "true")

    warnings, warning_codes = evaluate_real_visual_guard(allow_real_provider=True)

    assert warning_codes == ["REAL_FEATURE_REQUIRES_HUMAN_CONFIRMATION"]


def test_api_visual_request_reports_multimodal_guard(monkeypatch):
    _clear(monkeypatch)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise esta tela",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [{"type": "screenshot", "name": "tela.png", "content": "fake"}],
        },
    )
    data = response.json()
    visual = data["visual_qa_analysis"]

    assert response.status_code == 200
    assert "MULTIMODAL_PROVIDER_DISABLED" in visual["warning_codes"]
    assert "MULTIMODAL_PROVIDER_REQUIRES_EXPLICIT_AUTH" in visual["warning_codes"]
    # Nenhum provider multimodal foi tentado.
    assert visual["provider_attempted"] is False


def test_no_multimodal_call_even_with_flags_in_standard_pytest(monkeypatch):
    monkeypatch.setenv(FLAG_MULTIMODAL, "true")
    monkeypatch.setenv(FLAG_VISUAL, "true")

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise esta tela",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "allow_real_provider": True,
            "artifacts": [{"type": "screenshot", "name": "tela.png", "content": "fake"}],
        },
    )
    data = response.json()
    visual = data["visual_qa_analysis"]

    assert response.status_code == 200
    assert visual["provider_attempted"] is False
    assert "REAL_FEATURE_REQUIRES_HUMAN_CONFIRMATION" in visual["warning_codes"]
    assert visual["requires_human_review"] is True


def test_release_gate_still_blocks_visual_even_fully_flagged(monkeypatch):
    monkeypatch.setenv(FLAG_MULTIMODAL, "true")
    monkeypatch.setenv(FLAG_VISUAL, "true")

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode liberar?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "allow_real_provider": True,
            "artifacts": [{"type": "screenshot", "name": "tela.png", "content": "fake"}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["release_gate"]["can_advance"] is False
