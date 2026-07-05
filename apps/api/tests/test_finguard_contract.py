import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FAKE_QA_PAYLOAD = {
    "origin_system": "finguard",
    "task_type": "qa_report_analysis",
    "message": "Analisar relatório QA fake do FinGuard.",
    "provider": "local_qa",
    "allow_real_provider": False,
    "artifacts": [
        {
            "type": "text",
            "name": "finguard-qa-fake.txt",
            "content": "125 passed, 0 failed. Build successful.",
        }
    ],
    "metadata": {"environment": "fake", "source": "contract-test"},
}


def test_fake_finguard_payload_accepted():
    response = client.post("/api/orchestrate", json=FAKE_QA_PAYLOAD)

    data = response.json()

    assert response.status_code == 200
    assert data["origin_system"] == "finguard"
    assert data["project_id"] == "finguard"
    assert data["status"] == "ok"
    assert data["qa"] is not None
    assert data["qa"]["analysis_source"] == "local_text_heuristic"
    assert data["qa"]["status"] == "pass"


def test_finguard_local_origin_recognized():
    payload = dict(FAKE_QA_PAYLOAD, origin_system="finguard-local")
    response = client.post("/api/orchestrate", json=payload)

    data = response.json()

    assert response.status_code == 200
    assert data["project_id"] == "finguard-local"
    assert data["task_allowed_for_project"] is True
    assert not any("desconhecido" in w for w in data["task_warnings"])


def test_finguard_path_metadata_rejected_and_never_read(tmp_path):
    real_file = tmp_path / "finguard-relatorio.md"
    real_file.write_text("CONTEUDO-REAL-FINGUARD-NUNCA-LIDO", encoding="utf-8")

    payload = dict(
        FAKE_QA_PAYLOAD,
        artifacts=[
            {
                "type": "qa_report",
                "name": "finguard-relatorio.md",
                "metadata": {"path": str(real_file)},
            }
        ],
    )
    response = client.post("/api/orchestrate", json=payload)

    data = response.json()

    assert response.status_code == 200
    assert "ARTIFACT_PATH_REJECTED" in data["warning_codes"]
    assert "ARTIFACT_READER_PATH_NOT_ALLOWED" in data["warning_codes"]
    assert "CONTEUDO-REAL-FINGUARD-NUNCA-LIDO" not in json.dumps(data, ensure_ascii=False)


def test_finguard_reader_blocked_even_if_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("PEDROCORE_ARTIFACT_READER_ENABLED", "true")
    monkeypatch.setenv("PEDROCORE_ARTIFACT_ALLOWED_DIRS", str(tmp_path))

    real_file = tmp_path / "relatorio.txt"
    real_file.write_text("125 passed - CONTEUDO-QUE-NAO-DEVE-VAZAR", encoding="utf-8")

    payload = dict(
        FAKE_QA_PAYLOAD,
        artifacts=[
            {
                "type": "text",
                "name": "relatorio.txt",
                "metadata": {"path": str(real_file)},
            }
        ],
    )
    response = client.post("/api/orchestrate", json=payload)

    data = response.json()

    assert response.status_code == 200
    assert "ARTIFACT_READER_PATH_NOT_ALLOWED" in data["warning_codes"]
    assert "CONTEUDO-QUE-NAO-DEVE-VAZAR" not in json.dumps(data, ensure_ascii=False)


def test_finguard_file_path_and_absolute_path_rejected():
    for key in ("path", "file_path", "absolute_path"):
        payload = dict(
            FAKE_QA_PAYLOAD,
            artifacts=[
                {
                    "type": "text",
                    "name": "x.txt",
                    "metadata": {key: "C:\\Projetos\\finguard\\arquivo.txt"},
                }
            ],
        )
        response = client.post("/api/orchestrate", json=payload)
        data = response.json()

        assert response.status_code == 200
        assert "ARTIFACT_PATH_REJECTED" in data["warning_codes"], f"chave: {key}"


def test_finguard_release_gate_with_failure_blocks():
    payload = dict(
        FAKE_QA_PAYLOAD,
        task_type="release_gate_review",
        artifacts=[
            {
                "type": "qa_report",
                "name": "qa.txt",
                "content": "3 tests failed with AssertionError",
            }
        ],
    )
    response = client.post("/api/orchestrate", json=payload)

    data = response.json()

    assert response.status_code == 200
    assert data["release_gate"]["can_advance"] is False
    assert data["release_gate"]["blocked_reason"] is not None
    assert "RELEASE_GATE_BLOCKED" in data["warning_codes"]


def test_finguard_release_gate_clean_local_advances():
    payload = dict(FAKE_QA_PAYLOAD, task_type="release_gate_review")
    response = client.post("/api/orchestrate", json=payload)

    data = response.json()

    assert response.status_code == 200
    assert data["provider_used"] == "local_qa"
    assert data["release_gate"]["can_advance"] is True


def test_finguard_real_provider_blocked_by_default():
    payload = dict(FAKE_QA_PAYLOAD, provider="gemini")
    response = client.post("/api/orchestrate", json=payload)

    data = response.json()

    assert response.status_code == 200
    assert data["safe_mode_blocked"] is True
    assert data["provider_used"] == "mock"
    assert "PROVIDER_REAL_BLOCKED" in data["warning_codes"]


def test_finguard_unlisted_task_generates_policy_warning():
    payload = dict(FAKE_QA_PAYLOAD, task_type="general_chat")
    response = client.post("/api/orchestrate", json=payload)

    data = response.json()

    assert response.status_code == 200
    assert data["task_allowed_for_project"] is False
    assert "PROJECT_TASK_NOT_ALLOWED" in data["warning_codes"]


def test_finguard_exploration_task_allowed():
    payload = dict(
        FAKE_QA_PAYLOAD,
        task_type="exploratory_test_plan",
        message="Planejar exploração manual do dashboard do FinGuard.",
    )
    response = client.post("/api/orchestrate", json=payload)

    data = response.json()

    assert response.status_code == 200
    assert data["task_allowed_for_project"] is True
    assert data["exploration"] is not None
    assert data["exploration"]["can_execute_actions"] is False
