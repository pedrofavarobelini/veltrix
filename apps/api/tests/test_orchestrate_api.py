import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH_ENV_VAR = "PEDROCORE_INTERNAL_API_KEY"
AUTH_HEADER = "X-PedroCore-Api-Key"

CLEAN_SUCCESS = "All tests passed. 0 failed. Build successful."

AUDIT_REQUIRED_FIELDS = [
    "audit_id",
    "origin_system",
    "task_type",
    "provider_requested",
    "provider_used",
    "fallback_used",
    "safe_mode_blocked",
    "status",
    "timestamp",
    "latency_ms",
    "risk_level",
    "can_advance",
]


def test_orchestrate_exists_and_works_in_dev_mode(monkeypatch):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)

    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "mock"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["answer"]
    assert "INTERNAL_AUTH_NOT_CONFIGURED" in data["warning_codes"]


def test_orchestrate_warnings_have_severity(monkeypatch):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)

    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "mock"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["warnings"] != []
    for item in data["warnings"]:
        assert set(item.keys()) >= {"code", "message", "severity"}
        assert item["severity"] in {"info", "warning", "error", "critical"}


def test_orchestrate_returns_qa_for_qa_task(monkeypatch):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": CLEAN_SUCCESS}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["qa"] is not None
    assert data["qa"]["analysis_source"] == "local_text_heuristic"
    assert data["qa"]["status"] == "pass"
    assert data["release_gate"] is None


def test_orchestrate_returns_release_gate_for_gate_task(monkeypatch):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode avançar?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": CLEAN_SUCCESS}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["release_gate"] is not None
    assert data["release_gate"]["can_advance"] is True
    assert data["provider_used"] == "local_qa"


def test_orchestrate_returns_full_audit(monkeypatch):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": CLEAN_SUCCESS}],
        },
    )

    data = response.json()
    audit = data["audit"]

    assert response.status_code == 200
    for field in AUDIT_REQUIRED_FIELDS:
        assert field in audit, f"campo ausente no audit: {field}"
    assert audit["latency_ms"] >= 0
    assert audit["provider_requested"] == "mock"
    assert audit["provider_used"] == "mock"


def test_orchestrate_audit_does_not_leak_artifact_content(monkeypatch):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)

    secret_content = "password: SegredoUltraConfidencial123!"
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": secret_content}],
        },
    )

    data = response.json()

    assert response.status_code == 200
    audit_dump = json.dumps(data["audit"], ensure_ascii=False)
    assert "SegredoUltraConfidencial123" not in audit_dump
    assert "QA_RISK_CRITICAL" in data["warning_codes"]


def test_orchestrate_rejects_path_and_does_not_read_file(monkeypatch, tmp_path):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)

    real_file = tmp_path / "arquivo-real.md"
    real_file.write_text("CONTEUDO-DO-DISCO-QUE-NAO-PODE-APARECER", encoding="utf-8")

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise este arquivo",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [
                {"type": "qa_report", "name": "arquivo-real.md", "metadata": {"path": str(real_file)}}
            ],
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert "ARTIFACT_PATH_REJECTED" in data["warning_codes"]
    assert data["status"] == "blocked"
    assert data["blocked_reason"] is not None
    assert "CONTEUDO-DO-DISCO-QUE-NAO-PODE-APARECER" not in json.dumps(
        data, ensure_ascii=False
    )
    assert data["qa"]["can_advance"] is False


def test_orchestrate_auth_missing_header_blocks(monkeypatch):
    monkeypatch.setenv(AUTH_ENV_VAR, "chave-de-teste-local")

    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "mock"},
    )

    data = response.json()

    assert response.status_code == 401
    assert data["error_code"] == "INTERNAL_AUTH_MISSING"
    assert data["status"] == "blocked"
    assert "chave-de-teste-local" not in json.dumps(data)


def test_orchestrate_auth_wrong_header_blocks(monkeypatch):
    monkeypatch.setenv(AUTH_ENV_VAR, "chave-de-teste-local")

    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "mock"},
        headers={AUTH_HEADER: "chave-errada"},
    )

    data = response.json()

    assert response.status_code == 401
    assert data["error_code"] == "INTERNAL_AUTH_INVALID"
    assert "chave-de-teste-local" not in json.dumps(data)


def test_orchestrate_auth_correct_header_allows(monkeypatch):
    monkeypatch.setenv(AUTH_ENV_VAR, "chave-de-teste-local")

    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "mock"},
        headers={AUTH_HEADER: "chave-de-teste-local"},
    )

    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert "INTERNAL_AUTH_NOT_CONFIGURED" not in data["warning_codes"]


def test_chat_stays_free_even_with_internal_key_configured(monkeypatch):
    monkeypatch.setenv(AUTH_ENV_VAR, "chave-de-teste-local")

    response = client.post(
        "/api/chat",
        json={"message": "Teste", "provider": "mock"},
    )

    assert response.status_code == 200
    assert response.json()["answer"]


def test_orchestrate_task_warnings_kept_for_compatibility(monkeypatch):
    monkeypatch.delenv(AUTH_ENV_VAR, raising=False)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise",
            "provider": "mock",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert any("sem artefatos enviados" in w for w in data["task_warnings"])
    assert "QA_NO_ARTIFACTS" in data["warning_codes"]


def test_providers_endpoint_still_works():
    response = client.get("/api/providers")

    assert response.status_code == 200
    assert {p["name"] for p in response.json()} >= {"mock", "gemini"}
