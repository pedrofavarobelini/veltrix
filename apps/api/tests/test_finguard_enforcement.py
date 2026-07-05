import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ALLOWED_FINGUARD_TASKS = [
    "qa_report_analysis",
    "qa_failure_diagnosis",
    "release_gate_review",
    "exploratory_test_plan",
    "manual_exploration_report",
    "assisted_exploration_review",
    "artifact_summary",
    "technical_explanation",
]

DANGEROUS_TASKS = [
    "execute_command",
    "run_migration",
    "delete_records",
    "write_file_to_repo",
    "deploy_to_production",
    "drop_database",
]


def finguard_payload(**overrides):
    payload = {
        "origin_system": "finguard",
        "task_type": "qa_report_analysis",
        "message": "Analisar relatório QA fake.",
        "provider": "local_qa",
        "artifacts": [{"type": "text", "content": "125 passed, 0 failed."}],
    }
    payload.update(overrides)
    return payload


def test_all_allowed_finguard_tasks_accepted():
    for task in ALLOWED_FINGUARD_TASKS:
        response = client.post("/api/orchestrate", json=finguard_payload(task_type=task))
        data = response.json()

        assert response.status_code == 200, f"task: {task}"
        assert data["task_allowed_for_project"] is True, f"task: {task}"
        assert data["error_code"] != "PROJECT_POLICY_BLOCKED", f"task: {task}"


def test_dangerous_tasks_are_hard_blocked():
    for task in DANGEROUS_TASKS:
        response = client.post("/api/orchestrate", json=finguard_payload(task_type=task))
        data = response.json()

        assert response.status_code == 200, f"task: {task}"
        assert data["status"] == "blocked", f"task nao bloqueada: {task}"
        assert data["blocked_reason"] is not None
        assert data["error_code"] == "PROJECT_POLICY_BLOCKED"
        assert data["provider_used"] == "none"
        assert data["qa"] is None


def test_dangerous_payload_keys_are_blocked():
    response = client.post(
        "/api/orchestrate",
        json=finguard_payload(metadata={"command": "rm -rf /"}),
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "blocked"
    assert "PROJECT_POLICY_BLOCKED" in data["warning_codes"]
    # O comando nunca é executado nem repassado a provider.
    assert data["provider_used"] == "none"


def test_finguard_critical_unlisted_task_blocked():
    # 'code_help' não está na lista do FinGuard; como é medium, apenas warning.
    response = client.post("/api/orchestrate", json=finguard_payload(task_type="code_help"))
    data = response.json()
    assert data["status"] != "blocked"
    assert data["task_allowed_for_project"] is False

    # Task crítica desconhecida do FinGuard: 'unknown' vira criticality low → não bloqueia;
    # mas task crítica reconhecida fora da lista deve bloquear (nenhuma existe hoje para
    # finguard, todas as críticas são permitidas — validado com origem unknown abaixo).


def test_unknown_origin_critical_task_blocked():
    response = client.post(
        "/api/orchestrate",
        json={
            "origin_system": "sistema_desconhecido",
            "task_type": "release_gate_review",
            "message": "Pode liberar?",
            "provider": "local_qa",
            "artifacts": [{"type": "text", "content": "125 passed, 0 failed."}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "blocked"
    assert "PROJECT_POLICY_BLOCKED" in data["warning_codes"]
    assert data["release_gate"] is None


def test_unknown_origin_low_task_still_warns_only():
    response = client.post(
        "/api/orchestrate",
        json={
            "origin_system": "sistema_desconhecido",
            "task_type": "general_chat",
            "message": "Oi",
            "provider": "mock",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert "UNKNOWN_ORIGIN_SYSTEM" in data["warning_codes"]


def test_finguard_cannot_use_reader_or_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("PEDROCORE_ARTIFACT_READER_ENABLED", "true")
    monkeypatch.setenv("PEDROCORE_ARTIFACT_ALLOWED_DIRS", str(tmp_path))
    real_file = tmp_path / "qa.txt"
    real_file.write_text("CONTEUDO-QUE-NAO-PODE-VAZAR", encoding="utf-8")

    response = client.post(
        "/api/orchestrate",
        json=finguard_payload(
            artifacts=[{"type": "text", "name": "qa.txt", "metadata": {"path": str(real_file)}}]
        ),
    )
    data = response.json()

    assert response.status_code == 200
    assert "ARTIFACT_READER_PATH_NOT_ALLOWED" in data["warning_codes"]
    assert "ARTIFACT_PATH_REJECTED" in data["warning_codes"]
    assert "CONTEUDO-QUE-NAO-PODE-VAZAR" not in json.dumps(data, ensure_ascii=False)


def test_finguard_write_intent_blocked():
    response = client.post(
        "/api/orchestrate",
        json=finguard_payload(task_type="write_report_to_disk"),
    )
    data = response.json()

    assert data["status"] == "blocked"
    assert data["error_code"] == "PROJECT_POLICY_BLOCKED"


def test_internal_api_key_still_enforced_for_finguard(monkeypatch):
    monkeypatch.setenv("PEDROCORE_INTERNAL_API_KEY", "chave-local-de-teste")

    without_key = client.post("/api/orchestrate", json=finguard_payload())
    assert without_key.status_code == 401
    assert without_key.json()["error_code"] == "INTERNAL_AUTH_MISSING"

    with_key = client.post(
        "/api/orchestrate",
        json=finguard_payload(),
        headers={"X-PedroCore-Api-Key": "chave-local-de-teste"},
    )
    assert with_key.status_code == 200
    assert with_key.json()["status"] == "ok"


def test_finguard_real_provider_still_blocked_by_default():
    response = client.post(
        "/api/orchestrate", json=finguard_payload(provider="gemini")
    )
    data = response.json()

    assert response.status_code == 200
    assert data["safe_mode_blocked"] is True
    assert "PROVIDER_REAL_BLOCKED" in data["warning_codes"]


def test_chat_legacy_not_broken_by_enforcement():
    response = client.post(
        "/api/chat", json={"message": "Teste", "provider": "mock"}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["task_warnings"] == []
