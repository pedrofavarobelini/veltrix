import importlib.util

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.ocr.service import ocr_service

client = TestClient(app)

FLAG = "PEDROCORE_OCR_ENABLED"

FAKE_IMAGE_BYTES = b"fake-image-bytes"

pytesseract_installed = importlib.util.find_spec("pytesseract") is not None


def test_ocr_disabled_blocks(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)

    result = ocr_service.extract_from_bytes(FAKE_IMAGE_BYTES)

    assert result.attempted is False
    assert result.executed is False
    assert result.text is None
    assert "OCR_NOT_ENABLED" in result.warning_codes


@pytest.mark.skipif(
    pytesseract_installed,
    reason="pytesseract instalado neste ambiente; cenário de indisponibilidade não se aplica",
)
def test_ocr_enabled_without_dependency_is_handled(monkeypatch):
    monkeypatch.setenv(FLAG, "true")

    result = ocr_service.extract_from_bytes(FAKE_IMAGE_BYTES)

    assert result.attempted is True
    assert result.executed is False
    assert result.text is None
    assert "OCR_DEPENDENCY_UNAVAILABLE" in result.warning_codes


def test_ocr_result_always_requires_human_review(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)

    result = ocr_service.extract_from_bytes(FAKE_IMAGE_BYTES)

    assert result.requires_human_review is True


def test_visual_analysis_reports_ocr_disabled(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [{"type": "screenshot", "name": "tela.png", "content": "fake"}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert "OCR_NOT_ENABLED" in data["visual_qa_analysis"]["warning_codes"]
    assert data["visual_qa_analysis"]["ocr_attempted"] is False


def test_release_gate_never_advances_with_ocr_only_evidence(monkeypatch):
    # Mesmo com OCR "ligado" (sem dependência), evidência visual continua
    # insuficiente para release gate.
    monkeypatch.setenv(FLAG, "true")

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode liberar?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "image", "name": "evidencia.png", "content": "fake"}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["release_gate"]["can_advance"] is False


def test_no_external_service_in_ocr_path(monkeypatch):
    # O serviço de OCR não possui nenhum cliente HTTP; este teste garante que o
    # módulo não importa bibliotecas de rede.
    import app.modules.ocr.service as ocr_mod

    source = open(ocr_mod.__file__, encoding="utf-8").read()
    for banned in ("requests", "httpx", "aiohttp", "urllib"):
        assert banned not in source, f"dependência de rede proibida no OCR: {banned}"
