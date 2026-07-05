from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_legacy_request_without_artifacts_keeps_compatibility():
    response = client.post(
        "/api/chat",
        json={"message": "Teste", "mode": "tecnico", "provider": "mock"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["artifact_count"] == 0
    assert data["artifact_types"] == []
    assert data["artifact_warnings"] == []
    assert data["task_allowed_for_project"] is True
    assert data["qa_skeleton"] is None
    assert data["task_warnings"] == []


def test_accepts_markdown_artifact_with_content():
    response = client.post(
        "/api/chat",
        json={
            "message": "Resuma este artefato",
            "provider": "mock",
            "task_type": "artifact_summary",
            "origin_system": "finguard",
            "artifacts": [
                {"type": "markdown", "name": "doc.md", "content": "# Doc\nConteúdo."}
            ],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["artifact_count"] == 1
    assert data["artifact_types"] == ["markdown"]
    assert data["artifact_warnings"] == []


def test_accepts_qa_report_artifact_and_returns_skeleton():
    response = client.post(
        "/api/chat",
        json={
            "message": "Analise este relatório de QA",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [
                {"type": "qa_report", "name": "qa.md", "content": "Todos os smoke tests passaram."}
            ],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["artifact_count"] == 1
    assert data["qa_skeleton"] is not None
    assert data["qa_skeleton"]["status"] == "not_analyzed"
    assert data["qa_skeleton"]["can_advance"] is not True
    assert data["qa_skeleton"]["confidence"] == 0.0
    assert data["qa_skeleton"]["findings"] == []
    assert data["qa_skeleton"]["failures"] == []


def test_artifact_without_content_generates_warning():
    response = client.post(
        "/api/chat",
        json={
            "message": "Teste",
            "provider": "mock",
            "artifacts": [{"type": "log", "name": "vazio.log"}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert any("sem conteúdo" in w for w in data["artifact_warnings"])
    assert any("sem conteúdo" in w for w in data["task_warnings"])


def test_visual_artifact_generates_not_supported_warning():
    response = client.post(
        "/api/chat",
        json={
            "message": "Analise esta tela",
            "provider": "mock",
            "task_type": "qa_failure_diagnosis",
            "origin_system": "finguard",
            "artifacts": [{"type": "screenshot", "name": "tela.png", "content": "fake"}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert any("análise visual" in w for w in data["artifact_warnings"])
    assert any("análise visual" in w for w in data["qa_skeleton"]["warnings"])


def test_unknown_artifact_type_does_not_break():
    response = client.post(
        "/api/chat",
        json={
            "message": "Teste",
            "provider": "mock",
            "artifacts": [{"type": "tipo_estranho", "content": "abc"}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert any("desconhecido" in w for w in data["artifact_warnings"])


def test_finguard_qa_report_analysis_is_allowed():
    response = client.post(
        "/api/chat",
        json={
            "message": "Analise",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": "relatório"}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["task_allowed_for_project"] is True
    assert not any("não listado em allowed_tasks" in w for w in data["task_warnings"])


def test_finguard_general_chat_warns_but_does_not_break():
    response = client.post(
        "/api/chat",
        json={
            "message": "Oi",
            "provider": "mock",
            "task_type": "general_chat",
            "origin_system": "finguard",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["task_allowed_for_project"] is False
    assert any("não listado em allowed_tasks" in w for w in data["task_warnings"])


def test_unknown_origin_generates_policy_warning():
    response = client.post(
        "/api/chat",
        json={
            "message": "Teste",
            "provider": "mock",
            "origin_system": "sistema_inexistente",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert any(
        "não validado contra política de projeto" in w for w in data["task_warnings"]
    )


def test_qa_task_without_artifacts_generates_warning():
    response = client.post(
        "/api/chat",
        json={
            "message": "Analise o QA",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert any("sem artefatos enviados" in w for w in data["task_warnings"])
    assert any("sem artefatos enviados" in w for w in data["qa_skeleton"]["warnings"])


def test_release_gate_fallback_returns_skeleton_with_fallback_warning():
    response = client.post(
        "/api/chat",
        json={
            "message": "Pode avançar?",
            "provider": "inexistente",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": "evidências"}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["fallback_used"] is True
    assert data["qa_skeleton"] is not None
    assert data["qa_skeleton"]["can_advance"] is not True
    assert any(
        "Fallback Mock usado em tarefa crítica" in w
        for w in data["qa_skeleton"]["warnings"]
    )
    assert any(
        "Fallback Mock usado em tarefa crítica" in w for w in data["task_warnings"]
    )


def test_non_qa_task_returns_no_skeleton():
    response = client.post(
        "/api/chat",
        json={
            "message": "Explique FastAPI",
            "provider": "mock",
            "task_type": "technical_explanation",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["qa_skeleton"] is None


def test_providers_endpoint_still_works():
    response = client.get("/api/providers")

    assert response.status_code == 200
    assert {p["name"] for p in response.json()} >= {"mock", "gemini"}
