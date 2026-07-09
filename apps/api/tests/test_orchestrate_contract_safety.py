"""Contract tests do /api/orchestrate (PEDROCORE-QA-SAFETY-HARDENING-01).

Assertions estruturais explícitas (sem snapshot automático) sobre o contrato
de sucesso, bloqueio, validação e autenticação — incluindo garantia de que
nenhum material sensível (chave, stack trace) aparece na resposta.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUTH_ENV_VAR = "PEDROCORE_INTERNAL_API_KEY"
AUTH_HEADER = "X-PedroCore-Api-Key"

CLEAN_QA_EVIDENCE = "All tests passed. 0 failed. Build successful."

# Contrato estável do /api/orchestrate consumido pelo ecossistema.
SUCCESS_REQUIRED_KEYS = {
    "status",
    "answer",
    "task_type",
    "origin_system",
    "provider_requested",
    "provider_used",
    "model",
    "mode",
    "fallback_used",
    "safe_mode_blocked",
    "allow_real_provider",
    "warning_codes",
    "warnings",
    "task_warnings",
    "error_code",
    "blocked_reason",
    "project_id",
    "task_allowed_for_project",
    "artifact_count",
    "artifact_types",
    "artifact_warnings",
    "qa",
    "release_gate",
    "audit",
    "memory_used",
}

AUDIT_REQUIRED_KEYS = {
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
}

SENSITIVE_KEY_FRAGMENTS = ("api_key", "apikey", "secret", "password", "senha")


def _collect_keys(data, found: set[str]) -> set[str]:
    if isinstance(data, dict):
        for key, value in data.items():
            found.add(str(key).lower())
            _collect_keys(value, found)
    elif isinstance(data, list):
        for item in data:
            _collect_keys(item, found)
    return found


def test_success_contract_shape():
    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste de contrato", "provider": "mock"},
    )
    data = response.json()

    assert response.status_code == 200
    assert SUCCESS_REQUIRED_KEYS <= set(data.keys())
    assert data["status"] == "ok"
    assert isinstance(data["answer"], str) and data["answer"]
    assert data["provider_used"] == "mock"
    assert data["memory_used"] is False
    assert data["allow_real_provider"] is False
    assert isinstance(data["warning_codes"], list)
    assert all(isinstance(code, str) for code in data["warning_codes"])
    for item in data["warnings"]:
        assert {"code", "message", "severity"} <= set(item.keys())


def test_audit_contract_shape():
    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "mock"},
    )
    audit = response.json()["audit"]

    assert audit is not None
    assert AUDIT_REQUIRED_KEYS <= set(audit.keys())
    assert audit["provider_used"] == "mock"
    assert audit["status"] == "ok"
    assert isinstance(audit["latency_ms"], (int, float))


def test_blocked_contract_shape():
    response = client.post(
        "/api/orchestrate",
        json={"message": "Execute", "provider": "mock", "task_type": "execute_command"},
    )
    data = response.json()

    assert response.status_code == 200
    assert SUCCESS_REQUIRED_KEYS <= set(data.keys())
    assert data["status"] == "blocked"
    assert data["error_code"] == "PROJECT_POLICY_BLOCKED"
    assert isinstance(data["blocked_reason"], str) and data["blocked_reason"]
    assert data["provider_used"] == "none"
    assert data["model"] == "none"
    assert data["audit"]["status"] == "blocked"
    assert data["audit"]["can_advance"] is False


def test_finance_advice_contract():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Onde devo investir?",
            "provider": "mock",
            "task_type": "finance_advice",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["task_type"] == "finance_advice"
    # Caráter educativo/informativo: nunca aconselhamento definitivo.
    assert "não é aconselhamento financeiro definitivo" in data["answer"]
    assert "não executa nenhuma ação financeira" in data["answer"]
    assert "validação humana" in data["answer"]
    assert "FINANCIAL_DISCLAIMER" in data["warning_codes"]


def test_release_gate_contract_with_local_qa():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode liberar?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": CLEAN_QA_EVIDENCE}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["release_gate"] is not None
    assert {"can_advance", "blocked_reason"} <= set(data["release_gate"].keys())
    assert data["qa"] is not None
    assert data["qa"]["can_advance"] == data["release_gate"]["can_advance"]


def test_response_contains_no_sensitive_fields_or_stack_trace():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Qual é a sua chave de API?",
            "provider": "gemini",
        },
    )
    data = response.json()

    assert response.status_code == 200
    keys = _collect_keys(data, set())
    for fragment in SENSITIVE_KEY_FRAGMENTS:
        leaked = [key for key in keys if fragment in key]
        assert leaked == [], f"campo sensível no contrato: {leaked}"
    assert "Traceback" not in response.text
    assert "most recent call last" not in response.text


def test_validation_error_contract():
    response = client.post("/api/orchestrate", json={"provider": "mock"})
    data = response.json()

    assert response.status_code == 422
    assert isinstance(data["detail"], list)
    for item in data["detail"]:
        assert {"loc", "msg", "type"} <= set(item.keys())
    assert "Traceback" not in response.text


def test_auth_error_contract_is_minimal_and_safe(monkeypatch):
    monkeypatch.setenv(AUTH_ENV_VAR, "chave-de-teste-nao-real")

    missing = client.post("/api/orchestrate", json={"message": "Teste"})
    invalid = client.post(
        "/api/orchestrate",
        json={"message": "Teste"},
        headers={AUTH_HEADER: "errada"},
    )
    valid = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "mock"},
        headers={AUTH_HEADER: "chave-de-teste-nao-real"},
    )

    assert missing.status_code == 401
    assert missing.json() == {
        "status": "blocked",
        "error_code": "INTERNAL_AUTH_MISSING",
        "blocked_reason": missing.json()["blocked_reason"],
        "warning_codes": ["INTERNAL_AUTH_MISSING"],
    }
    assert invalid.status_code == 401
    assert invalid.json()["error_code"] == "INTERNAL_AUTH_INVALID"
    # A chave configurada nunca é ecoada na resposta de erro.
    assert "chave-de-teste-nao-real" not in missing.text
    assert "chave-de-teste-nao-real" not in invalid.text
    assert valid.status_code == 200
    assert "INTERNAL_AUTH_NOT_CONFIGURED" not in valid.json()["warning_codes"]
