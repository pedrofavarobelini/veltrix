import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.providers.base import BaseAIProvider, ProviderResponse
from app.modules.providers.registry import provider_registry
from app.modules.observability.sanitizer import sanitize_payload
from app.modules.observability.service import (
    FLAG_ENABLED,
    FLAG_MAX_ENTRIES,
    FLAG_QA_FORCE_TOTAL_FAILURE,
    observability_service,
)
from app.modules.report_memory.service import FLAG_PERSISTENCE, report_memory_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_observability(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.setenv(FLAG_MAX_ENTRIES, "20")
    monkeypatch.setenv(FLAG_PERSISTENCE, "off")
    observability_service.reset()
    report_memory_service.reset()
    yield
    observability_service.reset()
    report_memory_service.reset()


def _latest_detail() -> dict:
    listing = client.get("/api/observability/executions").json()
    assert listing["items"]
    execution_id = listing["items"][0]["execution_id"]
    response = client.get(f"/api/observability/executions/{execution_id}")
    assert response.status_code == 200
    return response.json()


def test_observability_is_default_off_and_blocked_in_production(monkeypatch):
    monkeypatch.delenv(FLAG_ENABLED, raising=False)
    assert client.get("/api/observability/status").json()["enabled"] is False
    assert client.get("/api/observability/executions").status_code == 404

    monkeypatch.setenv(FLAG_ENABLED, "true")
    monkeypatch.setenv("APP_ENV", "production")
    assert client.get("/api/observability/status").json()["enabled"] is False
    assert client.get("/api/observability/executions").status_code == 404


def test_mock_success_records_audit_public_response_and_evaluation():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Teste local",
            "provider": "mock",
            "task_type": "finance_advice",
            "origin_system": "finguard",
        },
    )
    assert response.status_code == 200

    detail = _latest_detail()
    assert detail["audit_id"] == response.json()["audit"]["audit_id"]
    assert detail["provider_requested"] == "mock"
    assert detail["provider_selected"] == "mock"
    assert detail["provider_effective"] == "mock"
    assert detail["provider_attempts"][0]["result"] == "success"
    assert detail["fallback"] is False
    assert detail["public_response"] == response.json()["answer"]
    assert detail["evaluation"] is not None
    assert detail["retry"] == {"attempted": False, "count": 0}
    assert response.json()["project_id"] == "finguard"
    assert detail["result_returned"]["project_id"] == "finguard"
    assert detail["result_returned"]["model"] == response.json()["model"]


def test_local_qa_and_fallback_are_visible_and_filterable():
    local_response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise",
            "provider": "local_qa",
            "task_type": "qa_report_analysis",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": "All tests passed. 0 failed."}],
        },
    )
    assert local_response.status_code == 200

    fallback_response = client.post(
        "/api/orchestrate",
        json={"message": "Teste", "provider": "provider_inexistente"},
    )
    assert fallback_response.json()["fallback_used"] is True

    local_items = client.get(
        "/api/observability/executions",
        params={"origin": "finguard", "provider": "local_qa", "fallback": "false"},
    ).json()["items"]
    assert len(local_items) == 1
    assert local_items[0]["task"] == "qa_report_analysis"

    fallback_items = client.get(
        "/api/observability/executions", params={"fallback": "true"}
    ).json()["items"]
    assert len(fallback_items) == 1
    detail = client.get(
        f"/api/observability/executions/{fallback_items[0]['execution_id']}"
    ).json()
    assert detail["provider_requested"] == "provider_inexistente"
    assert detail["provider_effective"] == "mock"
    assert detail["provider_attempts"][-1]["result"] == "fallback_success"
    assert detail["fallback_reason"]


def test_provider_timeout_uses_visible_safe_fallback(monkeypatch):
    class SlowProvider(BaseAIProvider):
        name = "slow_qa"
        label = "Slow QA"
        default_model = "slow-qa-v1"
        real_provider = False

        @property
        def is_configured(self) -> bool:
            return True

        async def generate_response(self, **_kwargs) -> ProviderResponse:
            await asyncio.sleep(0.2)
            return ProviderResponse(answer="tarde", provider=self.name, model=self.default_model)

    monkeypatch.setitem(provider_registry._providers, "slow_qa", SlowProvider())
    monkeypatch.setenv("PEDROCORE_PROVIDER_TIMEOUT_SECONDS", "0.05")

    response = client.post(
        "/api/orchestrate",
        json={"message": "Teste sintético", "provider": "slow_qa"},
    )
    data = response.json()
    assert response.status_code == 200
    assert data["fallback_used"] is True
    assert data["provider_used"] == "mock"
    assert data["error_code"] == "PROVIDER_TIMEOUT"

    detail = _latest_detail()
    assert detail["provider_attempts"][0]["result"] == "timeout"
    assert detail["provider_attempts"][-1]["result"] == "fallback_success"
    assert detail["fallback_reason"] == "Provider excedeu o tempo limite; fallback seguro aplicado."


def test_payload_and_errors_are_sanitized_without_full_financial_context():
    sensitive_payload = {
        "message": "Meu email pedro@example.com e token=abc123",
        "system_prompt": "prompt interno",
        "metadata": {"authorization": "Bearer super-secret-token"},
        "context": {
            "financial_context": {
                "debts": [{"title": "Cartao", "amount": "999.00"}],
                "accounts": [{"balance": "1000.00"}],
            }
        },
    }
    sanitized, removed = sanitize_payload(sensitive_payload)
    dump = json.dumps(sanitized, ensure_ascii=False)

    for forbidden in [
        "pedro@example.com",
        "abc123",
        "super-secret-token",
        "prompt interno",
        "999.00",
        "1000.00",
    ]:
        assert forbidden not in dump
    assert sanitized["context"]["financial_context"]["omitted"] is True
    assert set(removed) >= {
        "message",
        "system_prompt",
        "metadata.authorization",
        "context.financial_context",
    }


def test_orchestration_record_never_stores_secret_fields_or_values():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Analise token=segredo123",
            "provider": "mock",
            "context": {
                "financial_context": {
                    "debts": [{"title": "Dado financeiro", "amount": "777.00"}]
                }
            },
            "metadata": {"api_key": "chave-que-nao-pode-vazar"},
        },
    )
    assert response.status_code == 200
    detail = _latest_detail()
    dump = json.dumps(detail, ensure_ascii=False)
    assert "segredo123" not in dump
    assert "Dado financeiro" not in dump
    assert "777.00" not in dump
    assert "chave-que-nao-pode-vazar" not in dump
    assert "context.financial_context" in detail["removed_fields"]
    assert "metadata.api_key" in detail["removed_fields"]


def test_report_analysis_and_memory_ingestion_are_recorded(monkeypatch):
    report = {
        "project_id": "finguard",
        "report_type": "qa_run",
        "source": "finguard",
        "run_id": "QA-OBS-01",
        "branch": "docs-checkpoint",
        "commit": "abc1234",
        "status": "passed",
        "summary": "All tests passed. release gate aprovado.",
        "findings": ["0 failed"],
    }

    analyzed = client.post("/api/reports/analyze", json=report)
    assert analyzed.status_code == 200
    monkeypatch.setenv(FLAG_PERSISTENCE, "memory")
    ingested = client.post("/api/reports/ingest", json=report)
    assert ingested.status_code == 200
    assert ingested.json()["stored"] is True

    listing = client.get(
        "/api/observability/executions", params={"origin": "finguard"}
    ).json()["items"]
    assert {item["task"] for item in listing} == {"qa_report_analysis", "report_ingestion"}

    ingest_summary = next(item for item in listing if item["task"] == "report_ingestion")
    detail = client.get(
        f"/api/observability/executions/{ingest_summary['execution_id']}"
    ).json()
    assert detail["payload_sanitized"]["branch"] == "docs-checkpoint"
    assert detail["payload_sanitized"]["commit"] == "abc1234"
    assert detail["evaluation"] is not None
    assert detail["signals"]
    assert detail["memory_created"] is True
    assert detail["memory_id"]
    assert detail["release_gate"]["can_advance"] is True


def test_ring_buffer_respects_configured_limit(monkeypatch):
    monkeypatch.setenv(FLAG_MAX_ENTRIES, "10")
    for index in range(12):
        response = client.post(
            "/api/chat",
            json={"message": f"Teste {index}", "provider": "mock"},
        )
        assert response.status_code == 200

    listing = client.get(
        "/api/observability/executions", params={"limit": 100}
    ).json()
    assert listing["total"] == 10
    assert len(listing["items"]) == 10


def test_unexpected_pipeline_error_is_recorded_sanitized(monkeypatch):
    from app.modules.orchestration.service import orchestration_service

    async def fail(_payload, _caller=None):
        raise RuntimeError("provider falhou token=segredo-erro")

    monkeypatch.setattr(orchestration_service, "_execute_pipeline", fail)
    error_client = TestClient(app, raise_server_exceptions=False)
    response = error_client.post(
        "/api/chat", json={"message": "Teste", "provider": "mock"}
    )
    assert response.status_code == 500

    detail = _latest_detail()
    assert detail["status"] == "error"
    assert "segredo-erro" not in (detail["error"] or "")
    assert "[REDACTED]" in (detail["error"] or "")


def test_execution_record_distinguishes_identity_from_declared_origin(monkeypatch):
    """Etapa 2: a observabilidade separa identidade autenticada, origem
    declarada, provider solicitado e provider efetivo — sem segredos."""
    internal_key = "chave-interna-de-teste-nunca-real"
    monkeypatch.setenv("PEDROCORE_INTERNAL_API_KEY", internal_key)

    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Teste de identidade",
            "provider": "mock",
            "task_type": "assistant_chat",
            "origin_system": "finguard",
        },
        headers={"X-PedroCore-Api-Key": internal_key},
    )
    assert response.status_code == 200

    detail = _latest_detail()
    caller = detail["caller"]

    assert caller["authenticated"] is True
    assert caller["origin_system_declared"] == "finguard"
    # Chave global compartilhada: a alegação é registrada, nunca vira identidade.
    assert caller["origin_validation"] == "not_trusted"
    assert caller["identity_strength"] == "ambiguous"
    assert caller["project_id_authenticated"] == "shared_or_unknown"
    assert caller["caller_role"] == "common_consumer"
    assert caller["provider_selection_mode"] == "explicit"
    assert detail["provider_effective"] == "mock"
    assert internal_key not in json.dumps(detail, ensure_ascii=False)


def test_execution_record_distinguishes_planned_and_effective_binding():
    """Etapa 3: a observabilidade separa provider/model planejado do efetivo."""
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Teste de binding",
            "provider": "mock",
            "model": "mock-v1",
            "task_type": "assistant_chat",
            "origin_system": "pedrocore",
        },
    )
    assert response.status_code == 200

    binding = _latest_detail()["binding"]

    assert binding["provider_requested"] == "mock"
    assert binding["model_requested"] == "mock-v1"
    assert binding["model_selected"] == "mock-v1"
    assert binding["model_effective"] == response.json()["model"]
    assert binding["model_source"] == "local_fixed"
    assert binding["selection_mode"] == "explicit"


def test_total_provider_failure_hook_is_qa_only_and_diagnosed(monkeypatch):
    monkeypatch.setenv(FLAG_QA_FORCE_TOTAL_FAILURE, "true")
    error_client = TestClient(app, raise_server_exceptions=False)
    response = error_client.post(
        "/api/orchestrate",
        json={
            "origin_system": "finguard",
            "task_type": "finance_advice",
            "message": "Cenário sintético",
            "provider": "mock",
        },
    )
    assert response.status_code == 500
    detail = _latest_detail()
    assert detail["status"] == "error"
    assert detail["origin_system"] == "finguard"
    assert detail["provider_requested"] == "mock"
    assert "QA_TOTAL_PROVIDER_FAILURE" in (detail["error"] or "")

    observability_service.reset()
    monkeypatch.setenv("APP_ENV", "production")
    response = client.post(
        "/api/orchestrate",
        json={
            "origin_system": "finguard",
            "task_type": "finance_advice",
            "message": "Cenário sintético",
            "provider": "mock",
        },
    )
    assert response.status_code == 200
